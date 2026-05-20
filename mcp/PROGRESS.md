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
- **2026-05-20** — Phase 1 observability shipped to dev (PR #22):
  - `observability.enabled: true` in both top-level and `env.dev` blocks of `wrangler.jsonc`
  - `src/log.ts` emits structured JSON via `console.log`, auto-attaches `timestamp` + `version`
  - `list_tables`, `query`, `describe_namespace` instrumented with `outcome` + `duration_ms`; `query` also logs `sql`, `r2_sql_ms`, `r2_sql_status`, `rows_returned`, `rows_total`
  - Outcome enum: `ok`, `validation_error`, `partition_filter_error`, `catalog_unavailable`, `namespace_not_found`, `r2_sql_unreachable`, `r2_sql_http_error`, `r2_sql_query_error`, `exception`
  - Verified end-to-end via `wrangler tail --env dev` + MCP Inspector: `ok` (list_tables), `partition_filter_error` (query), `r2_sql_http_error` (query, status 400) all observed with correct field shape
  - Dropped the `oxfmt` format script
- **2026-05-20** — Deploy workflows inject `ACCOUNT_ID` and `BUCKET_NAME` Worker vars via `wrangler deploy --var`, sourced from GitHub repo variables `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_R2_BUCKET`. Removes dashboard-only var management; ensures dev/prod parity from CI. (Committed to `dev` as `0fe0966`, not yet merged.)

## Pending release

Merged to `main` and live on dev (`mcp-dev.bedrock.bio`), but won't reach prod until the next GitHub release. The same release event publishes the MCP worker, the Python package, and the R client — releases are batched (see "Release cadence" below).

- Dev/prod environment split
- Phase 1 observability
- Workflow-injected `ACCOUNT_ID` / `BUCKET_NAME` (once `dev` → `main` PR lands)

## In progress

(none — Phase 1 complete on dev)

## Queued

### Phase 2: Analytics Engine
Builds on Phase 1's `logEvent()`. Adds an AE binding and extends the helper to dual-write (`console.log` + `writeDataPoint`). Refactor SQL parser to expose `extractTableRefs()` so aggregation by namespace/table is queryable. Enables SQL-queryable metrics for query volume, hot namespaces/tables, error rates, R2 SQL p95 latency.

Open schema decisions deferred to phase 2:
- Single shared AE dataset with an `environment` blob (preferred) vs. separate `mcp_events_dev` / `mcp_events_prod` datasets
- Log the SQL `text` or only a `sql_hash` for grouping

### Per-namespace bucket routing
Today `BUCKET_NAME` is a single Worker var, so the server can only query one R2 Data Catalog (one domain bucket). The manifest's `metadata_json` paths already point to per-namespace buckets (e.g. `s3://bedrock-bio-genetics/...`); when a second domain bucket goes live, parse the bucket host out of `metadata_json` in `catalog.ts` and route each `query` to the bucket containing the referenced tables. Single-bucket-per-call is a natural constraint of the R2 SQL API. Until then, single-bucket assumption holds (`CLOUDFLARE_R2_BUCKET = bedrock-bio-genetics`).

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
- **GitHub repo settings**: add `CLOUDFLARE_R2_BUCKET` as a repo variable (Settings → Secrets and variables → Actions → Variables) before the next merge to `main` so `mcp-deploy-dev` can inject it via `--var`.
