import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { type Catalog, validateReadOnly, findMissingPartitionFilters, formatResultWarning, extractTableRefs } from "./catalog.js";
import { logSession, logToolCall, fnv1a16, type CallRow, type QueryRow, type TableRow } from "./log.js";
import { version } from "../package.json";

interface Env extends Cloudflare.Env {
	ACCOUNT_ID: string;
	R2_BUCKET_NAME: string;
	R2_SQL_TOKEN: string;
}

const MANIFEST_URL = "https://data.bedrock.bio/manifest.json";
const CATALOG_TTL_MS = 5 * 60 * 1000;

export class BedrockBioMcpServer extends McpAgent<Env> {
	server = new McpServer({
		name: "Bedrock Bio",
		version,
		description:
			"Bedrock Bio computational biology data catalog. " +
			"IMPORTANT: All table and schema information is available through this server's tools. " +
			"Do NOT search the web for table schemas or data. " +
			"Use the list_tables tool to discover available tables, " +
			"then use describe_namespace to get column details for all tables in a namespace at once, " +
			"then use the query tool to run SQL. " +
			"ALWAYS include the citation for every namespace used in your response, " +
			"formatted as: Authors. Title. Journal Volume, Pages (Year). doi:URL. " +
			"Citations are provided in the list_tables and describe_namespace output.",
	});

	private catalog: Catalog | null = null;
	private catalogFetchedAt = 0;
	private sessionLogged = false;

	// One catalog load attempt per request. Returns { catalog, cached } so handlers can record
	// cache_hit and the manifest's published_at on each call. On transient errors we fall back
	// to the previously cached copy if one exists.
	private async loadCatalog(): Promise<{ catalog: Catalog; cached: boolean }> {
		const now = Date.now();
		if (this.catalog && now - this.catalogFetchedAt < CATALOG_TTL_MS) {
			return { catalog: this.catalog, cached: true };
		}

		try {
			const response = await fetch(MANIFEST_URL);
			if (!response.ok) throw new Error("Data catalog not available. Contact the administrator.");
			this.catalog = await response.json<Catalog>();
			this.catalogFetchedAt = now;
			return { catalog: this.catalog, cached: false };
		} catch (err) {
			if (this.catalog) return { catalog: this.catalog, cached: true };
			throw err;
		}
	}

	// MCP `initialize` handshake hook — first place we see clientInfo + protocolVersion.
	// Idempotent against DO restarts: in-memory flag prevents double-write within one
	// DO lifetime; cold starts may emit a duplicate session row, dedupe at query time.
	// TODO: country/colo/user_agent are populated empty for now — capturing them requires
	// plumbing the HTTP request through the agents/mcp SDK lifecycle. Track separately.
	async setInitializeRequest(initializeRequest: any): Promise<void> {
		await super.setInitializeRequest(initializeRequest);
		if (this.sessionLogged) return;
		this.sessionLogged = true;
		const params = initializeRequest?.params ?? {};
		logSession(this.env, {
			session_id: this.ctx.id.toString(),
			client_name: params.clientInfo?.name ?? "",
			client_version: params.clientInfo?.version ?? "",
			user_agent: "",
			protocol_version: params.protocolVersion ?? "",
			country: "",
			colo: "",
		});
	}

	async init() {
		this.server.registerTool(
			"list_tables",
			{
				title: "List Tables",
				description:
					"List all available tables grouped by namespace (data source), with descriptions, query instructions, " +
					"citations, and licensing. Call this first to discover what data is available before querying.",
				inputSchema: {},
			},
			async () => {
				const call_id = crypto.randomUUID();
				const t0 = Date.now();
				let outcome = "ok";
				let cached = false;
				let error_message = "";
				let manifest_published_at = "";
				try {
					let catalog: Catalog;
					try {
						const result = await this.loadCatalog();
						catalog = result.catalog;
						cached = result.cached;
						manifest_published_at = catalog.published_at ?? "";
					} catch (err) {
						outcome = "catalog_unavailable";
						error_message = err instanceof Error ? err.message : String(err);
						return { isError: true, content: [{ type: "text" as const, text: error_message }] };
					}

					const namespaces = Object.entries(catalog.namespaces).map(([ns, nsDef]) => ({
						namespace: ns,
						name: nsDef.name,
						description: nsDef.description,
						citation: nsDef.citation,
						source_url: nsDef.source_url,
						license: nsDef.license,
						instructions: nsDef.instructions || "",
						tables: Object.entries(nsDef.tables).map(([tableName, tableDef]) => ({
							table: tableName,
							qualified: `${ns}.${tableName}`,
							description: tableDef.description,
							instructions: tableDef.instructions || "",
						})),
					}));

					return { content: [{ type: "text" as const, text: JSON.stringify(namespaces, null, 2) }] };
				} catch (err) {
					outcome = "exception";
					error_message = err instanceof Error ? err.message : String(err);
					throw err;
				} finally {
					const call: CallRow = {
						call_id,
						session_id: this.ctx.id.toString(),
						tool: "list_tables",
						outcome,
						error_message: outcome === "ok" ? "" : error_message,
						tool_args: "{}",
						manifest_published_at,
						duration_ms: Date.now() - t0,
						cache_hit: cached ? 1 : 0,
					};
					logToolCall(this.env, call);
				}
			}
		);

		this.server.registerTool(
			"query",
			{
				title: "SQL Query",
				description:
					"Execute a read-only SQL query against Iceberg tables. " +
					"Do NOT guess table names — call list_tables and describe_namespace first. " +
					"\n\nEXAMPLE: " +
					"SELECT protein_id, gene_symbol FROM ukb_ppp.assays WHERE gene_symbol = 'GLP1R' LIMIT 10" +
					"\n\nRULES: " +
					"- Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH (CTEs) are allowed. No SQL comments (-- or /* */). " +
					"- For partitioned tables, every query MUST include a WHERE filter on EVERY partition_by column (see describe_namespace). Tables with no partition_by have no such requirement. Queries missing required partition filters are REJECTED. " +
					"- JOINs (INNER, LEFT, RIGHT, FULL OUTER, CROSS) and subqueries (FROM, IN, EXISTS, scalar) are supported, as are multi-table CTEs. Apply WHERE filters to bound intermediate join sizes; join large fact tables through dimension tables when possible. LATERAL is NOT supported. " +
					"- For NOT IN with nullable columns, use NOT EXISTS instead (NOT IN fails on nulls). " +
					"- No SELECT DISTINCT or UNION/INTERSECT/EXCEPT — use GROUP BY or separate queries. " +
					"- No COUNT(DISTINCT col) — use APPROX_DISTINCT(col). Avoid COUNT(DISTINCT) inside multi-way joins. " +
					"- No ARRAY_AGG, STRING_AGG, PERCENTILE_CONT — use APPROX_MEDIAN, APPROX_PERCENTILE_CONT, APPROX_TOP_K. " +
					"- No window functions (OVER), OFFSET, UNNEST, PIVOT, UNPIVOT, or QUALIFY. " +
					"- Always include a LIMIT clause. Use specific column names, not SELECT *. " +
					"- Filter on sort_by columns (see describe_namespace) when relevant for faster reads. " +
					"- Timestamps in RFC3339; time functions operate in UTC.",
				inputSchema: { sql: z.string().describe("Read-only SQL query (SELECT, SHOW, DESCRIBE, EXPLAIN, or WITH)") },
			},
			async ({ sql }) => {
				const call_id = crypto.randomUUID();
				const t0 = Date.now();
				let outcome = "ok";
				let cached = false;
				let error_message = "";
				let manifest_published_at = "";
				let r2_sql_ms = 0;
				let r2_sql_status = 0;
				let rows_returned = 0;
				let rows_total = 0;
				let bytes_scanned = 0;
				let files_scanned = 0;
				let r2_requests_count = 0;
				let r2_sql_error_code = 0;
				let r2_sql_request_id = "";
				try {
					const validationError = validateReadOnly(sql);
					if (validationError) {
						outcome = "validation_error";
						error_message = validationError;
						return { isError: true, content: [{ type: "text" as const, text: validationError }] };
					}

					let catalog: Catalog | null = null;
					try {
						const result = await this.loadCatalog();
						catalog = result.catalog;
						cached = result.cached;
						manifest_published_at = catalog.published_at ?? "";
					} catch {}

					if (catalog) {
						const missingFilters = findMissingPartitionFilters(sql, catalog);
						if (missingFilters.length > 0) {
							outcome = "partition_filter_error";
							const { ns, table, partitionCols, missing } = missingFilters[0];
							error_message = `Query on ${ns}.${table} is missing required partition filters: ${missing.join(", ")}. ` +
								`Every query must include a WHERE filter for all partition_by columns: ${partitionCols.join(", ")}.`;
							return {
								isError: true,
								content: [{
									type: "text" as const,
									text: `${error_message} If you need data across multiple partitions, run separate queries for each partition value.`,
								}],
							};
						}
					}

					// SECURITY: env.R2_SQL_TOKEN (R2 Admin R/W) is in scope here — any new outbound fetch in this Worker is a secret-exfil surface. See mcp/CLAUDE.md.
					const url = `https://api.sql.cloudflarestorage.com/api/v1/accounts/${this.env.ACCOUNT_ID}/r2-sql/query/${this.env.R2_BUCKET_NAME}`;
					const headers = {
						Authorization: `Bearer ${this.env.R2_SQL_TOKEN}`,
						"Content-Type": "application/json",
					};
					const body = JSON.stringify({ query: sql });

					const tFetch = Date.now();
					let response: Response | undefined;
					for (let attempt = 0; attempt < 2; attempt++) {
						try {
							response = await fetch(url, { method: "POST", headers, body });
							break;
						} catch {
							// retry once on network error
						}
					}
					r2_sql_ms = Date.now() - tFetch;
					if (!response) {
						outcome = "r2_sql_unreachable";
						error_message = "R2 SQL is unreachable";
						return { isError: true, content: [{ type: "text" as const, text: "R2 SQL is unreachable. Try again shortly." }] };
					}
					r2_sql_status = response.status;

					if (!response.ok) {
						outcome = "r2_sql_http_error";
						const text = await response.text();
						error_message = `R2 SQL HTTP ${response.status}: ${text}`;
						return { isError: true, content: [{ type: "text" as const, text: error_message }] };
					}

					const data = (await response.json()) as any;
					if (!data.success) {
						outcome = "r2_sql_query_error";
						const errs = data.errors ?? [];
						r2_sql_error_code = errs[0]?.code ?? 0;
						error_message = errs.map((e: any) => e.message).join("; ") || "Unknown error";
						const hint = error_message.includes("table not found") ? "Use the list_tables tool to discover available table names." : undefined;
						return {
							isError: true,
							content: [{ type: "text" as const, text: JSON.stringify({ error: error_message, sql, ...(hint ? { hint } : {}) }, null, 2) }],
						};
					}

					r2_sql_request_id = data.result?.request_id ?? "";
					bytes_scanned = data.result?.metrics?.bytes_scanned ?? 0;
					files_scanned = data.result?.metrics?.files_scanned ?? 0;
					r2_requests_count = data.result?.metrics?.r2_requests_count ?? 0;

					const columns = (data.result?.schema ?? []).map((s: { name: string }) => s.name);
					const allRows: Record<string, unknown>[] = data.result?.rows ?? [];
					rows_total = allRows.length;
					const maxRows = 100;
					const rows = allRows.slice(0, maxRows);
					rows_returned = rows.length;
					const warning = formatResultWarning(rows.length, allRows.length, sql, maxRows);

					const header = `Columns: ${columns.join(", ")}\nRows: ${rows.length}${warning}`;
					return { content: [{ type: "text" as const, text: `${header}\n\n${JSON.stringify(rows, null, 2)}` }] };
				} catch (err) {
					outcome = "exception";
					error_message = err instanceof Error ? err.message : String(err);
					throw err;
				} finally {
					const sql_hash = fnv1a16(sql);
					const session_id = this.ctx.id.toString();
					const call: CallRow = {
						call_id,
						session_id,
						tool: "query",
						outcome,
						error_message: outcome === "ok" ? "" : error_message,
						tool_args: "{}",
						manifest_published_at,
						duration_ms: Date.now() - t0,
						cache_hit: cached ? 1 : 0,
					};
					const query: QueryRow = {
						call_id,
						session_id,
						sql,
						sql_hash,
						outcome,
						r2_sql_request_id,
						r2_sql_ms,
						r2_sql_status,
						rows_returned,
						rows_total,
						bytes_scanned,
						files_scanned,
						r2_requests_count,
						r2_sql_error_code,
					};
					const tables: TableRow[] = extractTableRefs(sql).map((t) => ({
						call_id,
						session_id,
						sql_hash,
						namespace: t.ns,
						table: t.table,
						outcome,
					}));
					logToolCall(this.env, call, query, tables);
				}
			}
		);

		this.server.registerTool(
			"describe_namespace",
			{
				title: "Describe Namespace",
				description:
					"Get full details for all tables in a namespace: columns, types, descriptions, partition/sort keys, " +
					"related tables, query instructions, and citation. Call this after list_tables and before writing queries.",
				inputSchema: {
					namespace: z.string().describe("Namespace (e.g. 'ukb_ppp', 'dbsnp')"),
				},
			},
			async ({ namespace }) => {
				const call_id = crypto.randomUUID();
				const t0 = Date.now();
				let outcome = "ok";
				let cached = false;
				let error_message = "";
				let manifest_published_at = "";
				try {
					let catalog: Catalog;
					try {
						const result = await this.loadCatalog();
						catalog = result.catalog;
						cached = result.cached;
						manifest_published_at = catalog.published_at ?? "";
					} catch (err) {
						outcome = "catalog_unavailable";
						error_message = err instanceof Error ? err.message : String(err);
						return { isError: true, content: [{ type: "text" as const, text: error_message }] };
					}

					const nsDef = catalog.namespaces[namespace];
					if (!nsDef) {
						outcome = "namespace_not_found";
						const available = Object.keys(catalog.namespaces).join(", ");
						error_message = `Namespace '${namespace}' not found. Available: ${available}`;
						return { isError: true, content: [{ type: "text" as const, text: error_message }] };
					}

					const tables = Object.entries(nsDef.tables).map(([tableName, tableDef]) => {
						const table: Record<string, unknown> = {
							table: `${namespace}.${tableName}`,
							description: tableDef.description,
						};
						if (tableDef.instructions) table.instructions = tableDef.instructions;
						table.partition_by = tableDef.partition_by;
						table.sort_by = tableDef.sort_by;
						table.columns = tableDef.columns;
						if (Object.keys(tableDef.related_tables).length > 0) table.related_tables = tableDef.related_tables;
						return table;
					});

					return {
						content: [{
							type: "text" as const,
							text: JSON.stringify({ namespace, citation: nsDef.citation, tables }, null, 2),
						}],
					};
				} catch (err) {
					outcome = "exception";
					error_message = err instanceof Error ? err.message : String(err);
					throw err;
				} finally {
					const call: CallRow = {
						call_id,
						session_id: this.ctx.id.toString(),
						tool: "describe_namespace",
						outcome,
						error_message: outcome === "ok" ? "" : error_message,
						tool_args: JSON.stringify({ namespace }),
						manifest_published_at,
						duration_ms: Date.now() - t0,
						cache_hit: cached ? 1 : 0,
					};
					logToolCall(this.env, call);
				}
			}
		);
	}
}

const mcpHandler = BedrockBioMcpServer.serve("/mcp", { binding: "MCP_SERVER" });

export default {
	fetch(request: Request, env: Env, ctx: ExecutionContext) {
		const url = new URL(request.url);
		if (url.pathname === "/health") {
			return Response.json({ status: "ok", version });
		}
		return mcpHandler.fetch(request, env, ctx);
	},
};
