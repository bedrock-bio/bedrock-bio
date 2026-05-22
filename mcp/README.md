# bedrock-bio-mcp

Cloudflare Worker exposing Bedrock Bio's Iceberg-backed datasets to LLM clients via the [Model Context Protocol](https://modelcontextprotocol.io). The server translates natural-language tool calls into read-only [R2 SQL](https://developers.cloudflare.com/r2-sql/) queries, using a catalog manifest stored in R2 to advertise namespaces, tables, schemas, and per-dataset query guidance.

## Tools

- `list_tables` — Lists every namespace and table in the catalog with descriptions, citations, licenses, and per-namespace query hints.
- `describe_namespace` — Returns column-level detail for every table in a namespace: types, descriptions, partition/sort keys, related-table hints, citation.
- `query` — Executes a read-only SQL query (SELECT / WITH / SHOW / DESCRIBE / EXPLAIN) via R2 SQL. For partitioned tables, every `partition_by` column must appear in WHERE. Results are capped at 100 rows.

## Connecting

The server is mounted at `/mcp`. Health check at `/health`.

From Claude Desktop, via [mcp-remote](https://www.npmjs.com/package/mcp-remote):

```json
{
  "mcpServers": {
    "bedrock-bio": {
      "command": "npx",
      "args": ["mcp-remote", "https://<your-worker-domain>/mcp"]
    }
  }
}
```

## Development

```bash
npm install
npm run dev         # local Worker (wrangler dev)
npm test            # vitest
npm run type-check  # tsc --noEmit
npm run lint:fix    # oxlint
npm run deploy      # wrangler deploy
```

## Configuration

Required at runtime:

- `R2_SQL_TOKEN` — **R2 API token** with **Admin Read & Write** scope, created from Cloudflare dashboard → R2 object storage → Manage API tokens (the dedicated R2 token page, not the generic My Profile → API Tokens page). The "Workers R2 SQL: Read" permission on the generic page silently 401s against R2 SQL; "Admin Read only" on the R2 page also 401s despite the docs. Set as a Worker secret (`wrangler secret put R2_SQL_TOKEN`). Tokens are account-wide; rotate aggressively if exposed.
- `ACCOUNT_ID` — Cloudflare account ID for the R2 SQL endpoint. Injected as a Worker var at deploy time (`wrangler deploy --var ACCOUNT_ID:...`); CI sources it from a repo variable.
- `R2_BUCKET_NAME` — R2 bucket the Iceberg tables live in. Injected as a Worker var at deploy time the same way.

The catalog manifest is fetched at runtime from `https://data.bedrock.bio/manifest.json` — no R2 binding required.

Bindings (in `wrangler.jsonc`):

- `MCP_SERVER` (Durable Object) — per-session MCP agent state
- `MCP_EVENTS` (Analytics Engine) — structured event stream for queryable usage metrics (prod: `bedrock_bio_mcp_events`; dev: `bedrock_bio_mcp_events_dev`)

## Notes

- The catalog manifest is cached in-memory per Durable Object instance with a 5-minute TTL. Transient R2 errors fall back to the previous cached copy rather than failing in-flight requests.
- Query validation uses a small string scanner (not a full SQL parser) to strip string literals before checking for comments and required partition filters. See `src/catalog.test.ts` for the exact behavior, including pinned edge cases.
- R2 SQL enforces additional restrictions (no DISTINCT, no UNION/INTERSECT/EXCEPT, no window functions, no OFFSET, no UNNEST/PIVOT/QUALIFY, etc.). The `query` tool's description carries the current list as LLM guidance.
