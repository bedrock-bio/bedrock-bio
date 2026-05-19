export interface Catalog {
	version: number;
	namespaces: Record<string, CatalogNamespace>;
}

export interface CatalogNamespace {
	id: string;
	name: string;
	description: string;
	citation: Record<string, string | number>;
	source_url: string;
	license: string;
	instructions?: string;
	tables: Record<string, CatalogTable>;
}

export interface CatalogTable {
	description: string;
	instructions?: string;
	metadata_json?: string;
	partition_by: string[];
	sort_by: string[];
	related_tables: Record<string, Record<string, string>>;
	columns: CatalogColumn[];
}

export interface CatalogColumn {
	name: string;
	type: string;
	description: string;
	nullable: boolean;
	allowed_values?: string[];
}

const ALLOWED_VERBS = ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH"] as const;

// Replace single-quoted string literal contents with spaces (preserving length and structure)
// and flag any unquoted -- or /* */ comment. Double-quoted identifiers are preserved as-is so
// quoted column/table references still match. Handles SQL '' escape for embedded single quotes.
function scrub(sql: string): { stripped: string; commentFound: boolean } {
	let out = "";
	let commentFound = false;
	let i = 0;
	const n = sql.length;
	while (i < n) {
		const c = sql[i];
		const c2 = sql[i + 1];
		if (c === "-" && c2 === "-") {
			commentFound = true;
			while (i < n && sql[i] !== "\n") { out += " "; i++; }
			continue;
		}
		if (c === "/" && c2 === "*") {
			commentFound = true;
			out += "  "; i += 2;
			while (i < n && !(sql[i] === "*" && sql[i + 1] === "/")) { out += " "; i++; }
			if (i < n) { out += "  "; i += 2; }
			continue;
		}
		if (c === "'") {
			out += " "; i++;
			while (i < n) {
				if (sql[i] === "'" && sql[i + 1] === "'") { out += "  "; i += 2; }
				else if (sql[i] === "'") { out += " "; i++; break; }
				else { out += " "; i++; }
			}
			continue;
		}
		if (c === '"') {
			out += c; i++;
			while (i < n && sql[i] !== '"') { out += sql[i]; i++; }
			if (i < n) { out += sql[i]; i++; }
			continue;
		}
		out += c;
		i++;
	}
	return { stripped: out, commentFound };
}

export function validateReadOnly(sql: string): string | null {
	const { stripped, commentFound } = scrub(sql);
	if (commentFound) {
		return "SQL comments are not allowed.";
	}
	const upper = stripped.trim().toUpperCase();
	if (!ALLOWED_VERBS.some((p) => upper.startsWith(p))) {
		return "Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH queries are allowed.";
	}
	return null;
}

export interface MissingPartitionFilter {
	ns: string;
	table: string;
	partitionCols: string[];
	missing: string[];
}

export function findMissingPartitionFilters(sql: string, catalog: Catalog): MissingPartitionFilter[] {
	const { stripped } = scrub(sql);
	const upper = stripped.trim().toUpperCase();
	if (!upper.startsWith("SELECT") && !upper.startsWith("WITH")) return [];

	const results: MissingPartitionFilter[] = [];
	const tablePattern = /\bFROM\s+(\w+)\.(\w+)\b/gi;
	const whereIdx = upper.indexOf("WHERE");
	const whereClause = whereIdx !== -1 ? upper.slice(whereIdx) : "";

	let match: RegExpExecArray | null;
	while ((match = tablePattern.exec(stripped)) !== null) {
		const ns = match[1].toLowerCase();
		const table = match[2].toLowerCase();
		const tableDef = catalog.namespaces[ns]?.tables[table];
		if (!tableDef) continue;
		const partitionCols = tableDef.partition_by;
		if (partitionCols.length === 0) continue;
		const missing = partitionCols.filter((col) => !whereClause.includes(col.toUpperCase()));
		if (missing.length > 0) {
			results.push({ ns, table, partitionCols, missing });
		}
	}
	return results;
}

export function formatResultWarning(rowsLength: number, allRowsLength: number, sql: string, maxRows: number): string {
	if (allRowsLength > maxRows) {
		return ` (truncated from ${allRowsLength} to ${maxRows} rows — narrow your WHERE filters or add a smaller LIMIT)`;
	}
	const limitMatch = sql.match(/\bLIMIT\s+(\d+)\b/i);
	const limit = limitMatch ? parseInt(limitMatch[1], 10) : null;
	if (limit !== null && limit > 1 && rowsLength >= limit) {
		return " (query returned the maximum number of rows — results may be incomplete, consider narrowing filters or raising LIMIT)";
	}
	return "";
}
