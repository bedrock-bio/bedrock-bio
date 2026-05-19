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
npm run format      # oxfmt
npm run deploy      # wrangler deploy
```

## Configuration

Set via `wrangler secret put` (sensitive) or `vars` in `wrangler.jsonc`:

- `ACCOUNT_ID` — Cloudflare account ID for the R2 SQL endpoint
- `BUCKET_NAME` — R2 bucket the Iceberg tables live under
- `R2_SQL_TOKEN` — API token with R2 SQL + Data Catalog + R2 read scopes

Bindings (in `wrangler.jsonc`):

- `CATALOG_BUCKET` (R2) — holds `manifest.json`, produced by the bedrock-bio-dagster pipeline
- `MCP_OBJECT` (Durable Object) — per-session MCP agent state

## Notes

- The catalog manifest is cached in-memory per Durable Object instance with a 5-minute TTL. Transient R2 errors fall back to the previous cached copy rather than failing in-flight requests.
- Query validation uses a small string scanner (not a full SQL parser) to strip string literals before checking for comments and required partition filters. See `src/catalog.test.ts` for the exact behavior, including pinned edge cases.
- R2 SQL enforces additional restrictions (no DISTINCT, no UNION/INTERSECT/EXCEPT, no window functions, no OFFSET, no UNNEST/PIVOT/QUALIFY, etc.). The `query` tool's description carries the current list as LLM guidance.
