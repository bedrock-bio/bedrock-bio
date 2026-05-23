import { version } from "../package.json";

// AE positional schema lives in the tuple types below. Reordering breaks every saved
// analytics_engine/sql query that references blobN/doubleN by position; renaming a tuple
// label is free. See mcp/SCHEMA.md for the analyst-facing reference.

// mcp_sessions
type SessionsBlobs = [
	session_id: string,
	client_version: string,
	worker_version: string,
	user_agent: string,
	protocol_version: string,
	country: string,
	colo: string,
];

// mcp_calls
type CallsBlobs = [
	call_id: string,
	session_id: string,
	outcome: string,
	worker_version: string,
	error_message: string,
	tool_args: string,
	manifest_published_at: string,
];
type CallsDoubles = [
	duration_ms: number,
	cache_hit: number,
];

// mcp_queries
type QueriesBlobs = [
	call_id: string,
	session_id: string,
	sql: string,
	outcome: string,
	r2_sql_request_id: string,
];
type QueriesDoubles = [
	r2_sql_ms: number,
	r2_sql_status: number,
	rows_returned: number,
	rows_total: number,
	bytes_scanned: number,
	files_scanned: number,
	r2_requests_count: number,
	r2_sql_error_code: number,
];

// mcp_tables — one per (call, distinct touched table)
type TablesBlobs = [
	call_id: string,
	session_id: string,
	sql_hash: string,
	table: string,
	outcome: string,
];

export interface SessionRow {
	session_id: string;
	client_name: string;
	client_version: string;
	user_agent: string;
	protocol_version: string;
	country: string;
	colo: string;
}

export interface CallRow {
	call_id: string;
	session_id: string;
	tool: string;
	outcome: string;
	error_message: string;
	tool_args: string;
	manifest_published_at: string;
	duration_ms: number;
	cache_hit: number;
}

export interface QueryRow {
	call_id: string;
	session_id: string;
	sql: string;
	sql_hash: string;
	outcome: string;
	r2_sql_request_id: string;
	r2_sql_ms: number;
	r2_sql_status: number;
	rows_returned: number;
	rows_total: number;
	bytes_scanned: number;
	files_scanned: number;
	r2_requests_count: number;
	r2_sql_error_code: number;
}

export interface TableRow {
	call_id: string;
	session_id: string;
	sql_hash: string;
	namespace: string;
	table: string;
	outcome: string;
}

interface Env {
	MCP_SESSIONS?: AnalyticsEngineDataset;
	MCP_CALLS?: AnalyticsEngineDataset;
	MCP_QUERIES?: AnalyticsEngineDataset;
	MCP_TABLES?: AnalyticsEngineDataset;
}

const MAX_SQL_AE_LEN = 4900;

export function truncateSql(sql: string): string {
	return sql.length > MAX_SQL_AE_LEN ? sql.slice(0, MAX_SQL_AE_LEN) + "…[truncated]" : sql;
}

export function logSession(env: Env, row: SessionRow): void {
	console.log(JSON.stringify({ timestamp: new Date().toISOString(), version, event: "session_start", ...row }));
	if (!env.MCP_SESSIONS) return;
	const blobs: SessionsBlobs = [
		row.session_id,
		row.client_version,
		version,
		row.user_agent,
		row.protocol_version,
		row.country,
		row.colo,
	];
	tryWrite(env.MCP_SESSIONS, { blobs, doubles: [], indexes: [row.client_name] });
}

// Orchestrates the AE writes for a single tool call: one CALLS row (always), plus an optional
// QUERIES row for `query`-tool calls, plus zero-or-more TABLES rows for tools that touch data.
// CALLS lands first; if that write fails the call is unrecorded and we skip QUERIES/TABLES to
// avoid orphan child rows. Console.log emits exactly one JSON line per tool call carrying all
// the fields and the touched-table list, for human-readable ops debugging via wrangler tail.
export function logToolCall(
	env: Env,
	call: CallRow,
	query?: QueryRow,
	tables: TableRow[] = [],
): void {
	console.log(JSON.stringify({
		timestamp: new Date().toISOString(),
		version,
		event: "tool_call",
		...call,
		...(query ? { sql: query.sql, sql_hash: query.sql_hash, r2_sql_ms: query.r2_sql_ms, r2_sql_status: query.r2_sql_status, rows_returned: query.rows_returned, rows_total: query.rows_total } : {}),
		...(tables.length > 0 ? { tables: tables.map((t) => `${t.namespace}.${t.table}`) } : {}),
	}));

	const callBlobs: CallsBlobs = [
		call.call_id,
		call.session_id,
		call.outcome,
		version,
		call.error_message,
		call.tool_args,
		call.manifest_published_at,
	];
	const callDoubles: CallsDoubles = [call.duration_ms, call.cache_hit];
	if (!tryWrite(env.MCP_CALLS, { blobs: callBlobs, doubles: callDoubles, indexes: [call.tool] })) return;

	if (query) {
		const queryBlobs: QueriesBlobs = [
			query.call_id,
			query.session_id,
			truncateSql(query.sql),
			query.outcome,
			query.r2_sql_request_id,
		];
		const queryDoubles: QueriesDoubles = [
			query.r2_sql_ms,
			query.r2_sql_status,
			query.rows_returned,
			query.rows_total,
			query.bytes_scanned,
			query.files_scanned,
			query.r2_requests_count,
			query.r2_sql_error_code,
		];
		tryWrite(env.MCP_QUERIES, { blobs: queryBlobs, doubles: queryDoubles, indexes: [query.sql_hash] });
	}

	for (const t of tables) {
		const tableBlobs: TablesBlobs = [t.call_id, t.session_id, t.sql_hash, t.table, t.outcome];
		tryWrite(env.MCP_TABLES, { blobs: tableBlobs, doubles: [], indexes: [t.namespace] });
	}
}

function tryWrite(
	dataset: AnalyticsEngineDataset | undefined,
	point: { blobs: string[]; doubles: number[]; indexes: string[] },
): boolean {
	if (!dataset) return false;
	try {
		dataset.writeDataPoint(point);
		return true;
	} catch (err) {
		console.warn(`AE writeDataPoint failed: ${err instanceof Error ? err.message : String(err)}`);
		return false;
	}
}

// FNV-1a 32-bit, doubled to 16 hex chars (run over s and s + "\0" then concatenated).
// Not cryptographic — just a stable short fingerprint for GROUP BY on recurring SQL.
export function fnv1a16(s: string): string {
	return fnv1a32Hex(s) + fnv1a32Hex(s + "\0");
}

function fnv1a32Hex(s: string): string {
	let hash = 0x811c9dc5;
	for (let i = 0; i < s.length; i++) {
		hash ^= s.charCodeAt(i);
		hash = Math.imul(hash, 0x01000193);
	}
	return (hash >>> 0).toString(16).padStart(8, "0");
}
