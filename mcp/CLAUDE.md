# Bedrock Bio MCP Server

This project includes a connected MCP server (`bedrock-bio`) for querying computational biology datasets. For any questions about genes, proteins, variants, pQTLs, or genomic data, use the Bedrock Bio MCP tools (`list_tables`, `describe_namespace`, `query`) instead of searching the web.

`PROGRESS.md` is the source-of-truth punch list for MCP state — check it before planning new work.

## Security: Worker fetch surface

`src/index.ts` uses `env.R2_SQL_TOKEN` (R2 Admin Read & Write on the whole account — Cloudflare has no working narrower scope today; see `README.md` Configuration section) in exactly one outbound `fetch()` to the read-only R2 SQL endpoint. The runtime has no other code path that touches the token.

Any change that adds or modifies outbound `fetch()` in this Worker, adds new dependencies to `mcp/package.json`, or reads/logs `env` outside the existing site is the highest-scrutiny change category in this codebase — those are the only realistic paths to leak the token. Flag them explicitly in PR descriptions and during self-review, even if the surrounding change looks routine.
