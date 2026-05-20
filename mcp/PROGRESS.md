# MCP Server Progress

Punch list and roadmap for the Bedrock Bio MCP server. This file is the source of truth for MCP project state — update it as work lands.

## Done

- **2026-05-19** — Migrated `bedrock-bio-mcp` into this monorepo as `mcp/`; original repo archived
- **2026-05-20** — Dev/prod environment split shipped (PR #21):
  - Dev: `mcp-dev.bedrock.bio` → `bedrock-bio-mcp-dev` Worker, push-to-main deploys
  - Prod: `mcp.bedrock.bio` → `bedrock-bio-mcp` Worker, release-triggered deploys
  - `/health` returns `{status, version}` JSON; `version` imported from `package.json` and used by both `/health` and the `McpServer` constructor
  - Smoke-test step on both deploy workflows
  - Wrangler upgraded to `^4.93.0`
- **2026-05-20** — Revoked old over-scoped Cloudflare API token; replaced with narrowly-scoped `mcp-r2-sql-ro-prod` (Workers R2 SQL: Read only)
- **2026-05-20** — Removed `claude.yml` from `bedrock-bio-dagster` and deleted the unused `CLAUDE_CODE_OAUTH_TOKEN` secret (Claude Code subscription OAuth tokens are not for CI/non-interactive use)

## Pending release

Merged to `main` and live on dev (`mcp-dev.bedrock.bio`), but won't reach prod until the next GitHub release. The same release event publishes the MCP worker, the Python package, and the R client — releases are batched (see "Release cadence" below).

- Dev/prod environment split (above)
- Phase 1 observability (below, once committed)

## In progress

### Phase 1: Workers Logs + structured logging

- Enable `observability.enabled` in `wrangler.jsonc` (both env blocks)
- Add `src/log.ts` — single `logEvent()` that emits structured JSON via `console.log`
- Instrument 3 tool handlers (`list_tables`, `query`, `describe_namespace`) with `try/catch/finally`, capturing `outcome` + `duration_ms`
- For `query`: also capture R2 SQL upstream latency, HTTP status, row counts (returned + total), and the full SQL
- Outcome enum: `ok`, `validation_error`, `partition_filter_error`, `catalog_unavailable`, `namespace_not_found`, `r2_sql_unreachable`, `r2_sql_http_error`, `r2_sql_query_error`, `exception`
- Drop the `oxfmt` format script — the existing code is hand-formatted and the formatter was never actually run

## Queued

### Phase 2: Analytics Engine
Builds on Phase 1's `logEvent()`. Adds an AE binding and extends the helper to dual-write (`console.log` + `writeDataPoint`). Refactor SQL parser to expose `extractTableRefs()` so aggregation by namespace/table is queryable. Enables SQL-queryable metrics for query volume, hot namespaces/tables, error rates, R2 SQL p95 latency.

Open schema decisions deferred to phase 2:
- Single shared AE dataset with an `environment` blob (preferred) vs. separate `mcp_events_dev` / `mcp_events_prod` datasets
- Log the SQL `text` or only a `sql_hash` for grouping

### Uptime monitoring
External check on `/health`. Options: Cloudflare Health Checks (Pro), GitHub Actions cron + curl, or third-party (Better Uptime / UptimeRobot free tier).

### Rate limiting
Cloudflare Rate Limiting Rules on `mcp.bedrock.bio/*` — dashboard config, no code change. Caps abuse of a public endpoint that costs R2 SQL query dollars.

### User-facing docs + discoverability
- Section in `bedrock-bio-www` showing how to connect Claude Desktop / Claude Code / Cursor to the MCP server
- Submit to public MCP registry at `github.com/modelcontextprotocol/servers`

## Deferred (revisit when justified)

- **Logpush to R2** — long-term log retention. Wait until Workers Logs 24h/7d ceiling actually bites, or until there's a use case for loading logs into Iceberg via Dagster.
- **Sentry** (`@sentry/cloudflare`) — wait for error volume to justify.
- **CORS** for browser clients
- **API-key auth** for enterprise tier
- **Durable Object state retention review**
- **Cost dashboard** for R2 SQL query volume

## Release cadence

Don't cut releases for single fixes. A GitHub release event fan-outs to three publish workflows (`mcp-deploy-prod.yml`, `python-publish-prod.yml`, `r-build.yml`); R package releases have meaningful overhead and are the binding constraint. Queue work until a substantive bundle is ready.

## Out-of-repo follow-ups

- **`bedrock-bio-infra`**: replace global `CLOUDFLARE_API_KEY` in `.github/workflows/tofu.yml` with a scoped token (Zone:Edit + DNS:Edit + Workers:Edit + R2:Edit on specific resources). Lets you drop `CLOUDFLARE_EMAIL` too. Hygiene, not urgent.
