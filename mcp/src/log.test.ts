import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { logSession, logToolCall, truncateSql, fnv1a16, type CallRow, type QueryRow, type TableRow, type SessionRow } from "./log.js";
import { version } from "../package.json";

function mockDataset(impl?: () => void) {
	return { writeDataPoint: vi.fn(impl) } as unknown as AnalyticsEngineDataset;
}

const baseCall: CallRow = {
	call_id: "call-1",
	session_id: "session-1",
	tool: "list_tables",
	outcome: "ok",
	error_message: "",
	tool_args: "{}",
	manifest_published_at: "2026-05-22T15:30:00Z",
	duration_ms: 42,
	cache_hit: 1,
};

const baseQuery: QueryRow = {
	call_id: "call-1",
	session_id: "session-1",
	sql: "SELECT 1",
	sql_hash: fnv1a16("SELECT 1"),
	outcome: "ok",
	r2_sql_request_id: "req-1",
	r2_sql_ms: 500,
	r2_sql_status: 200,
	rows_returned: 1,
	rows_total: 1,
	bytes_scanned: 1024,
	files_scanned: 1,
	r2_requests_count: 1,
	r2_sql_error_code: 0,
};

const baseSession: SessionRow = {
	session_id: "session-1",
	client_name: "Claude Desktop",
	client_version: "1.4.2",
	user_agent: "",
	protocol_version: "2025-03-26",
	country: "",
	colo: "",
};

describe("fnv1a16", () => {
	it("returns 16 lowercase hex chars", () => {
		expect(fnv1a16("SELECT 1")).toMatch(/^[0-9a-f]{16}$/);
	});
	it("is deterministic", () => {
		expect(fnv1a16("SELECT 1")).toBe(fnv1a16("SELECT 1"));
	});
	it("differs for different inputs", () => {
		expect(fnv1a16("SELECT 1")).not.toBe(fnv1a16("SELECT 2"));
	});
});

describe("truncateSql", () => {
	it("passes through short SQL unchanged", () => {
		expect(truncateSql("SELECT 1")).toBe("SELECT 1");
	});
	it("truncates SQL longer than 4900 chars and appends marker", () => {
		const long = "a".repeat(5000);
		const result = truncateSql(long);
		expect(result.length).toBe(4900 + "…[truncated]".length);
		expect(result.endsWith("…[truncated]")).toBe(true);
		expect(result.startsWith("a".repeat(4900))).toBe(true);
	});
	it("does not truncate at exactly 4900 chars", () => {
		const exact = "a".repeat(4900);
		expect(truncateSql(exact)).toBe(exact);
	});
});

describe("logSession", () => {
	let logSpy: ReturnType<typeof vi.spyOn>;
	beforeEach(() => { logSpy = vi.spyOn(console, "log").mockImplementation(() => {}); });
	afterEach(() => { logSpy.mockRestore(); });

	it("writes a session_start JSON line and one MCP_SESSIONS row with pinned positions", () => {
		const MCP_SESSIONS = mockDataset();
		logSession({ MCP_SESSIONS }, baseSession);

		expect(logSpy).toHaveBeenCalledTimes(1);
		const parsed = JSON.parse(logSpy.mock.calls[0][0] as string);
		expect(parsed.event).toBe("session_start");
		expect(parsed.client_name).toBe("Claude Desktop");
		expect(parsed.version).toBe(version);

		const points = (MCP_SESSIONS as any).writeDataPoint.mock.calls;
		expect(points).toHaveLength(1);
		const p = points[0][0];
		expect(p.blobs).toEqual(["session-1", "1.4.2", version, "", "2025-03-26", "", ""]);
		expect(p.doubles).toEqual([]);
		expect(p.indexes).toEqual(["Claude Desktop"]);
	});

	it("still console.logs when MCP_SESSIONS binding is missing", () => {
		logSession({}, baseSession);
		expect(logSpy).toHaveBeenCalledTimes(1);
	});
});

describe("logToolCall", () => {
	let logSpy: ReturnType<typeof vi.spyOn>;
	let warnSpy: ReturnType<typeof vi.spyOn>;
	beforeEach(() => {
		logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
		warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
	});
	afterEach(() => {
		logSpy.mockRestore();
		warnSpy.mockRestore();
	});

	it("writes one CALLS row for non-query tools with pinned positions", () => {
		const MCP_CALLS = mockDataset();
		const MCP_QUERIES = mockDataset();
		const MCP_TABLES = mockDataset();
		logToolCall({ MCP_CALLS, MCP_QUERIES, MCP_TABLES }, baseCall);

		const c = (MCP_CALLS as any).writeDataPoint.mock.calls[0][0];
		expect(c.blobs).toEqual(["call-1", "session-1", "ok", version, "", "{}", "2026-05-22T15:30:00Z"]);
		expect(c.doubles).toEqual([42, 1]);
		expect(c.indexes).toEqual(["list_tables"]);
		expect((MCP_QUERIES as any).writeDataPoint).not.toHaveBeenCalled();
		expect((MCP_TABLES as any).writeDataPoint).not.toHaveBeenCalled();
	});

	it("writes CALLS + QUERIES + N TABLES rows for a query touching N tables", () => {
		const MCP_CALLS = mockDataset();
		const MCP_QUERIES = mockDataset();
		const MCP_TABLES = mockDataset();
		const sql_hash = fnv1a16("SELECT 1");
		const tables: TableRow[] = [
			{ call_id: "call-1", session_id: "session-1", sql_hash, namespace: "ukb_ppp", table: "pqtls", outcome: "ok" },
			{ call_id: "call-1", session_id: "session-1", sql_hash, namespace: "ukb_ppp", table: "assays", outcome: "ok" },
			{ call_id: "call-1", session_id: "session-1", sql_hash, namespace: "dbsnp", table: "variants", outcome: "ok" },
		];
		logToolCall({ MCP_CALLS, MCP_QUERIES, MCP_TABLES }, { ...baseCall, tool: "query" }, baseQuery, tables);

		expect((MCP_CALLS as any).writeDataPoint).toHaveBeenCalledTimes(1);
		expect((MCP_QUERIES as any).writeDataPoint).toHaveBeenCalledTimes(1);
		expect((MCP_TABLES as any).writeDataPoint).toHaveBeenCalledTimes(3);

		const q = (MCP_QUERIES as any).writeDataPoint.mock.calls[0][0];
		expect(q.blobs).toEqual(["call-1", "session-1", "SELECT 1", "ok", "req-1"]);
		expect(q.doubles).toEqual([500, 200, 1, 1, 1024, 1, 1, 0]);
		expect(q.indexes).toEqual([sql_hash]);

		const tableCalls = (MCP_TABLES as any).writeDataPoint.mock.calls;
		expect(tableCalls[0][0].blobs).toEqual(["call-1", "session-1", sql_hash, "pqtls", "ok"]);
		expect(tableCalls[0][0].indexes).toEqual(["ukb_ppp"]);
		expect(tableCalls[1][0].blobs[3]).toBe("assays");
		expect(tableCalls[2][0].blobs[3]).toBe("variants");
		expect(tableCalls[2][0].indexes).toEqual(["dbsnp"]);
	});

	it("writes CALLS + QUERIES + 0 TABLES for queries that failed pre-parse (e.g. validation_error)", () => {
		const MCP_CALLS = mockDataset();
		const MCP_QUERIES = mockDataset();
		const MCP_TABLES = mockDataset();
		logToolCall(
			{ MCP_CALLS, MCP_QUERIES, MCP_TABLES },
			{ ...baseCall, tool: "query", outcome: "validation_error" },
			{ ...baseQuery, outcome: "validation_error" },
			[],
		);
		expect((MCP_CALLS as any).writeDataPoint).toHaveBeenCalledTimes(1);
		expect((MCP_QUERIES as any).writeDataPoint).toHaveBeenCalledTimes(1);
		expect((MCP_TABLES as any).writeDataPoint).not.toHaveBeenCalled();
	});

	it("aborts QUERIES/TABLES writes when CALLS write fails", () => {
		const MCP_CALLS = mockDataset(() => { throw new Error("boom"); });
		const MCP_QUERIES = mockDataset();
		const MCP_TABLES = mockDataset();
		logToolCall(
			{ MCP_CALLS, MCP_QUERIES, MCP_TABLES },
			{ ...baseCall, tool: "query" },
			baseQuery,
			[{ call_id: "call-1", session_id: "session-1", sql_hash: "h", namespace: "ukb_ppp", table: "pqtls", outcome: "ok" }],
		);
		expect((MCP_CALLS as any).writeDataPoint).toHaveBeenCalledTimes(1);
		expect((MCP_QUERIES as any).writeDataPoint).not.toHaveBeenCalled();
		expect((MCP_TABLES as any).writeDataPoint).not.toHaveBeenCalled();
		expect(warnSpy).toHaveBeenCalledTimes(1);
	});

	it("tolerates a failing TABLES write without aborting subsequent TABLES writes", () => {
		let n = 0;
		const MCP_CALLS = mockDataset();
		const MCP_QUERIES = mockDataset();
		const MCP_TABLES = mockDataset(() => { n++; if (n === 1) throw new Error("transient"); });
		logToolCall(
			{ MCP_CALLS, MCP_QUERIES, MCP_TABLES },
			{ ...baseCall, tool: "query" },
			baseQuery,
			[
				{ call_id: "call-1", session_id: "session-1", sql_hash: "h", namespace: "a", table: "t1", outcome: "ok" },
				{ call_id: "call-1", session_id: "session-1", sql_hash: "h", namespace: "a", table: "t2", outcome: "ok" },
				{ call_id: "call-1", session_id: "session-1", sql_hash: "h", namespace: "a", table: "t3", outcome: "ok" },
			],
		);
		// All 3 TABLES write attempts happen; first throws (warned), other two succeed
		expect((MCP_TABLES as any).writeDataPoint).toHaveBeenCalledTimes(3);
		expect(warnSpy).toHaveBeenCalledTimes(1);
	});

	it("emits exactly one console.log per tool call regardless of fan-out", () => {
		const MCP_CALLS = mockDataset();
		const MCP_QUERIES = mockDataset();
		const MCP_TABLES = mockDataset();
		logToolCall(
			{ MCP_CALLS, MCP_QUERIES, MCP_TABLES },
			{ ...baseCall, tool: "query" },
			baseQuery,
			[
				{ call_id: "call-1", session_id: "session-1", sql_hash: "h", namespace: "a", table: "t1", outcome: "ok" },
				{ call_id: "call-1", session_id: "session-1", sql_hash: "h", namespace: "a", table: "t2", outcome: "ok" },
			],
		);
		expect(logSpy).toHaveBeenCalledTimes(1);
		const parsed = JSON.parse(logSpy.mock.calls[0][0] as string);
		expect(parsed.event).toBe("tool_call");
		expect(parsed.tables).toEqual(["a.t1", "a.t2"]);
		expect(parsed.sql_hash).toBe(baseQuery.sql_hash);
	});

	it("truncates sql for AE but keeps sql_hash over the full text", () => {
		const MCP_CALLS = mockDataset();
		const MCP_QUERIES = mockDataset();
		const longSql = "SELECT " + "x,".repeat(3000); // ~6000 chars
		const fullHash = fnv1a16(longSql);
		logToolCall(
			{ MCP_CALLS, MCP_QUERIES },
			{ ...baseCall, tool: "query" },
			{ ...baseQuery, sql: longSql, sql_hash: fullHash },
			[],
		);
		const q = (MCP_QUERIES as any).writeDataPoint.mock.calls[0][0];
		expect(q.blobs[2].length).toBeLessThanOrEqual(4900 + "…[truncated]".length);
		expect(q.blobs[2].endsWith("…[truncated]")).toBe(true);
		expect(q.indexes[0]).toBe(fullHash); // hash unchanged by truncation
	});
});
