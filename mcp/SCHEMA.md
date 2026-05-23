# MCP Server Analytics Schema

Four Cloudflare Analytics Engine datasets back the MCP server's observability layer. This doc is the canonical analyst-facing reference; the runtime-canonical positions live as typed tuples in `src/log.ts`. Any schema change must touch both.

**DO NOT REORDER positional slots.** AE stores data by position (`blob1`, `blob2`, `double1`, …), not by name. Renaming a slot is free — change the tuple label and any analytics query aliases. Reordering silently corrupts every saved query that references the old position. Appending to the end is free.

## Datasets and relationships

```
mcp_sessions       (1 per MCP connection)        ← protocol-layer dimension
   │ 1:N
   ▼
mcp_calls          (1 per tool invocation)       ← universal fact table
   │ 1:0..1                 │ 1:N
   ▼                        ▼
mcp_queries        mcp_tables                    ← type-specific extension + shared data dimension
(only for `query` tool)   (any tool that touches tables)
```

Foreign keys:
- `mcp_calls.session_id` → `mcp_sessions.session_id`
- `mcp_queries.call_id` → `mcp_calls.call_id`
- `mcp_tables.call_id` → `mcp_calls.call_id`
- `mcp_tables.sql_hash` → `mcp_queries.sql_hash` (denormalized for fast pattern joins)

Several fields are denormalized for query convenience (`session_id` on CALLS/QUERIES/TABLES; `outcome` repeated across three datasets; `sql_hash` on TABLES). The denormalization optimizes the most common analytics scans at the cost of bytes that don't matter on AE's per-write pricing model.

Future tool types beyond `query` (e.g., methods running on Modal) get their own type-specific extension dataset analogous to `mcp_queries`, linked to `mcp_calls` by `call_id`. `mcp_tables` already generalizes to "tables referenced by any tool call," not just SQL queries.

## `mcp_sessions`

One row per MCP connection, written when the client's `initialize` request arrives.

| Slot | Field | Type | Notes |
|---|---|---|---|
| blob1 | `session_id` | string (UUID) | PK; generated at DO construction |
| blob2 | `client_version` | string | from MCP `initialize` `clientInfo.version` |
| blob3 | `worker_version` | string | from `package.json` |
| blob4 | `user_agent` | string | raw HTTP `User-Agent`; fallback identifier when `clientInfo` is missing/sparse |
| blob5 | `protocol_version` | string | MCP protocol version from `initialize.params.protocolVersion` |
| blob6 | `country` | string | from `request.cf.country` |
| blob7 | `colo` | string | from `request.cf.colo` — Cloudflare data center serving the session |
| index | `client_name` | string | low-cardinality GROUP BY key (Claude Desktop, Cursor, mcp-remote, Inspector, …) |
| timestamp | (implicit) | — | acts as session `started_at` |

`session_duration_ms` is not stored — derive at query time as `MAX(timestamp) - MIN(timestamp)` over the matching `mcp_calls` rows.

## `mcp_calls`

One row per tool invocation, written in the handler's `finally` block.

| Slot | Field | Type | Notes |
|---|---|---|---|
| blob1 | `call_id` | string (UUID) | PK |
| blob2 | `session_id` | string (UUID) | FK to `mcp_sessions` |
| blob3 | `outcome` | string | full outcome enum (`ok`, `validation_error`, `partition_filter_error`, `catalog_unavailable`, `r2_sql_*`, `exception`) |
| blob4 | `worker_version` | string | denormalized — correlate outcomes to versions without joining SESSIONS |
| blob5 | `error_message` | string | populated only when `outcome != 'ok'`; bounded by AE's 5KB blob cap |
| blob6 | `tool_args` | string (JSON) | JSON-stringified tool input args, *excluding* fields with their own column. For `query`: `"{}"` (sql lives on QUERIES). For `describe_namespace`: `'{"namespace":"..."}'`. For `list_tables`: `"{}"`. |
| double1 | `duration_ms` | number | handler wall-clock latency |
| double2 | `cache_hit` | number | 0 or 1 — was the catalog manifest served from the DO cache for this call |
| index | `tool` | string | low-cardinality (currently 3 values: `list_tables`, `query`, `describe_namespace`) |

## `mcp_queries`

One row per `query` tool call (1:0..1 with CALLS — only `query` tool calls emit a row here).

| Slot | Field | Type | Notes |
|---|---|---|---|
| blob1 | `call_id` | string (UUID) | PK; FK to `mcp_calls` |
| blob2 | `session_id` | string (UUID) | FK (denormalized) |
| blob3 | `sql` | string | full SQL text. **Truncated to 4900 chars + `…[truncated]` marker if longer.** The `sql_hash` is always computed over the *full* untruncated text so pattern grouping stays correct. |
| blob4 | `outcome` | string | denormalized — failure analytics by pattern without joining CALLS |
| blob5 | `r2_sql_request_id` | string | from R2 SQL response `result.request_id`; correlate with Cloudflare backend logs / support tickets |
| double1 | `r2_sql_ms` | number | wall-clock around the R2 SQL `fetch()` |
| double2 | `r2_sql_status` | number | HTTP status code |
| double3 | `rows_returned` | number | rows sent in response (after the 100-row truncation cap) |
| double4 | `rows_total` | number | rows R2 SQL produced before truncation |
| double5 | `bytes_scanned` | number | from R2 SQL `result.metrics.bytes_scanned` — cost signal |
| double6 | `files_scanned` | number | from R2 SQL `result.metrics.files_scanned` — partition/sort effectiveness |
| double7 | `r2_requests_count` | number | from R2 SQL `result.metrics.r2_requests_count` — subrequest count |
| double8 | `r2_sql_error_code` | number | from R2 SQL `errors[0].code`; 0 on success — clean GROUP BY for failure categories |
| index | `sql_hash` | string | high-cardinality (FNV-1a 32-bit doubled to 16 hex chars over the full SQL) |

## `mcp_tables`

One row per (call, distinct touched table). Generalizes to any tool that references tables in the catalog, not just `query`.

| Slot | Field | Type | Notes |
|---|---|---|---|
| blob1 | `call_id` | string (UUID) | FK to `mcp_calls` |
| blob2 | `session_id` | string (UUID) | FK (denormalized) |
| blob3 | `sql_hash` | string | FK to `mcp_queries` (denormalized); empty for non-query tool refs |
| blob4 | `table` | string | e.g. `pqtls` |
| blob5 | `outcome` | string | denormalized — failed queries per table without joining |
| index | `namespace` | string | low-cardinality (one per namespace); primary GROUP BY for table analytics |

PK is `(call_id, namespace, table)`. `extractTableRefs()` deduplicates within a call so self-joins collapse to one row.

## Dev vs prod

Identical binding names across environments (so code is unchanged); dataset names suffixed `_dev` for the dev worker. Dev exists primarily to validate the AE write path on every deploy — it's not the analytics source of truth.

| Binding | Prod dataset | Dev dataset |
|---|---|---|
| `MCP_SESSIONS` | `mcp_sessions` | `mcp_sessions_dev` |
| `MCP_CALLS` | `mcp_calls` | `mcp_calls_dev` |
| `MCP_QUERIES` | `mcp_queries` | `mcp_queries_dev` |
| `MCP_TABLES` | `mcp_tables` | `mcp_tables_dev` |

## Sample analytics queries

Top tables by query volume:
```sql
SELECT index1 AS namespace, blob4 AS table, COUNT(*) AS queries
FROM mcp_tables
WHERE timestamp > NOW() - INTERVAL '7' DAY
GROUP BY namespace, table
ORDER BY queries DESC
LIMIT 20
```

P95 query latency by SQL pattern:
```sql
SELECT index1 AS sql_hash, quantileTDigest(0.95)(double1) AS p95_r2_sql_ms, COUNT(*) AS runs
FROM mcp_queries
WHERE blob4 = 'ok' AND timestamp > NOW() - INTERVAL '24' HOUR
GROUP BY sql_hash
ORDER BY p95_r2_sql_ms DESC
LIMIT 10
```

Sessions and their tool-call funnel (which clients are actually querying?):
```sql
SELECT s.index1 AS client, COUNT(DISTINCT s.blob1) AS sessions, COUNT(c.blob1) AS calls,
       SUM(CASE WHEN c.index1 = 'query' THEN 1 ELSE 0 END) AS queries
FROM mcp_sessions s
LEFT JOIN mcp_calls c ON c.blob2 = s.blob1
WHERE s.timestamp > NOW() - INTERVAL '30' DAY
GROUP BY client
ORDER BY sessions DESC
```

Failed queries clustered by error category:
```sql
SELECT c.blob3 AS outcome, double8 AS r2_sql_error_code, COUNT(*) AS n
FROM mcp_queries q JOIN mcp_calls c USING (blob1)
WHERE c.blob3 != 'ok' AND q.timestamp > NOW() - INTERVAL '24' HOUR
GROUP BY outcome, r2_sql_error_code
ORDER BY n DESC
```
