import { version } from "../package.json";

// AE positional schema — DO NOT REORDER. Renaming a slot is fine; reordering
// breaks any saved analytics_engine/sql query that references the old position.
// blobs:   [event_type, tool, outcome, version, sql_hash, sql, namespace, table]
// doubles: [duration_ms, r2_sql_ms, r2_sql_status, rows_returned, rows_total]
// indexes: [tool]

export interface LogEvent {
	event_type: string;
	tool: string;
	outcome: string;
	duration_ms: number;
	sql?: string;
	sql_hash?: string;
	namespace?: string;
	table?: string;
	r2_sql_ms?: number;
	r2_sql_status?: number;
	rows_returned?: number;
	rows_total?: number;
}

interface EnvWithEvents {
	MCP_EVENTS?: AnalyticsEngineDataset;
}

export function logEvent(env: EnvWithEvents, event: LogEvent): void {
	const sql_hash = event.sql_hash ?? (event.sql ? fnv1a16(event.sql) : undefined);
	const enriched = { ...event, ...(sql_hash ? { sql_hash } : {}) };

	console.log(JSON.stringify({ timestamp: new Date().toISOString(), version, ...enriched }));

	if (!env.MCP_EVENTS) return;
	try {
		env.MCP_EVENTS.writeDataPoint({
			blobs: [
				event.event_type,
				event.tool,
				event.outcome,
				version,
				sql_hash ?? "",
				event.sql ?? "",
				event.namespace ?? "",
				event.table ?? "",
			],
			doubles: [
				event.duration_ms,
				event.r2_sql_ms ?? 0,
				event.r2_sql_status ?? 0,
				event.rows_returned ?? 0,
				event.rows_total ?? 0,
			],
			indexes: [event.tool],
		});
	} catch (err) {
		console.warn(`MCP_EVENTS write failed: ${err instanceof Error ? err.message : String(err)}`);
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
