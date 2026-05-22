import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { logEvent, fnv1a16 } from "./log.js";
import { version } from "../package.json";

describe("fnv1a16", () => {
	it("returns 16 lowercase hex chars", () => {
		const h = fnv1a16("SELECT 1");
		expect(h).toMatch(/^[0-9a-f]{16}$/);
	});

	it("is deterministic", () => {
		expect(fnv1a16("SELECT * FROM ukb_ppp.assays")).toBe(fnv1a16("SELECT * FROM ukb_ppp.assays"));
	});

	it("differs for different inputs", () => {
		expect(fnv1a16("SELECT 1")).not.toBe(fnv1a16("SELECT 2"));
	});

	it("handles empty string", () => {
		expect(fnv1a16("")).toMatch(/^[0-9a-f]{16}$/);
	});
});

describe("logEvent", () => {
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

	it("writes a JSON line to console.log with timestamp and version", () => {
		logEvent({}, { event_type: "tool_call", tool: "list_tables", outcome: "ok", duration_ms: 42 });
		expect(logSpy).toHaveBeenCalledTimes(1);
		const parsed = JSON.parse(logSpy.mock.calls[0][0] as string);
		expect(parsed).toMatchObject({
			event_type: "tool_call",
			tool: "list_tables",
			outcome: "ok",
			duration_ms: 42,
			version,
		});
		expect(parsed.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
	});

	it("adds sql_hash to the console.log line when sql is present", () => {
		logEvent({}, { event_type: "tool_call", tool: "query", outcome: "ok", duration_ms: 10, sql: "SELECT 1" });
		const parsed = JSON.parse(logSpy.mock.calls[0][0] as string);
		expect(parsed.sql_hash).toBe(fnv1a16("SELECT 1"));
	});

	it("dual-writes to MCP_EVENTS with pinned blob/double/index positions", () => {
		const writeDataPoint = vi.fn();
		const env = { MCP_EVENTS: { writeDataPoint } as unknown as AnalyticsEngineDataset };
		logEvent(env, {
			event_type: "tool_call",
			tool: "query",
			outcome: "ok",
			duration_ms: 100,
			sql: "SELECT 1",
			r2_sql_ms: 50,
			r2_sql_status: 200,
			rows_returned: 1,
			rows_total: 1,
		});
		expect(writeDataPoint).toHaveBeenCalledTimes(1);
		const point = writeDataPoint.mock.calls[0][0];
		expect(point.blobs).toEqual([
			"tool_call",
			"query",
			"ok",
			version,
			fnv1a16("SELECT 1"),
			"SELECT 1",
			"",
			"",
		]);
		expect(point.doubles).toEqual([100, 50, 200, 1, 1]);
		expect(point.indexes).toEqual(["query"]);
	});

	it("fills missing blob slots with empty strings and missing doubles with 0", () => {
		const writeDataPoint = vi.fn();
		const env = { MCP_EVENTS: { writeDataPoint } as unknown as AnalyticsEngineDataset };
		logEvent(env, { event_type: "tool_call", tool: "list_tables", outcome: "ok", duration_ms: 5 });
		const point = writeDataPoint.mock.calls[0][0];
		expect(point.blobs).toEqual(["tool_call", "list_tables", "ok", version, "", "", "", ""]);
		expect(point.doubles).toEqual([5, 0, 0, 0, 0]);
	});

	it("uses caller-supplied sql_hash instead of recomputing", () => {
		const writeDataPoint = vi.fn();
		const env = { MCP_EVENTS: { writeDataPoint } as unknown as AnalyticsEngineDataset };
		logEvent(env, {
			event_type: "tool_call",
			tool: "query",
			outcome: "ok",
			duration_ms: 1,
			sql_hash: "deadbeefdeadbeef",
			namespace: "ukb_ppp",
			table: "assays",
		});
		const point = writeDataPoint.mock.calls[0][0];
		expect(point.blobs[4]).toBe("deadbeefdeadbeef");
		expect(point.blobs[6]).toBe("ukb_ppp");
		expect(point.blobs[7]).toBe("assays");
	});

	it("still console.logs when MCP_EVENTS is undefined", () => {
		logEvent({}, { event_type: "tool_call", tool: "list_tables", outcome: "ok", duration_ms: 1 });
		expect(logSpy).toHaveBeenCalledTimes(1);
	});

	it("swallows writeDataPoint errors and warns", () => {
		const writeDataPoint = vi.fn(() => {
			throw new Error("boom");
		});
		const env = { MCP_EVENTS: { writeDataPoint } as unknown as AnalyticsEngineDataset };
		expect(() =>
			logEvent(env, { event_type: "tool_call", tool: "list_tables", outcome: "ok", duration_ms: 1 }),
		).not.toThrow();
		expect(logSpy).toHaveBeenCalledTimes(1);
		expect(warnSpy).toHaveBeenCalledTimes(1);
		expect(warnSpy.mock.calls[0][0]).toMatch(/MCP_EVENTS write failed: boom/);
	});
});
