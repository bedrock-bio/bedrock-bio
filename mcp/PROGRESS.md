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
- **2026-05-20** — Deploy workflows inject `ACCOUNT_ID` and `R2_BUCKET_NAME` Worker vars via `wrangler deploy --var`, sourced from GitHub repo variables `CLOUDFLARE_ACCOUNT_ID` and `R2_BUCKET_NAME`. Removes dashboard-only var management; ensures dev/prod parity from CI.
- **2026-05-20** — Single-bucket consolidation. Decision: treat `bedrock-bio-genetics` as the sole data bucket going forward (no separate per-domain buckets). Unlocks cross-domain JOINs end-to-end through MCP (R2 SQL is bucket-scoped per URL path). Implementation:
  - Manifest fetched via HTTPS from `https://data.bedrock.bio/manifest.json` (same URL the R/Python clients use); dropped `CATALOG_BUCKET` R2 binding from `wrangler.jsonc`.
  - `R2_BUCKET_NAME` stays as a Worker var (kept as one knob for the future bucket rename); `R2_BUCKET_NAME = bedrock-bio-genetics` for now.
- **2026-05-21** — Cutover complete: `manifest.json` + `credentials.json` now served from `bedrock-bio-genetics` via `data.bedrock.bio` custom-domain mapping; `bedrock-bio-datasets` bucket retired. Credentials keys renamed `BB_R2_*` → `R2_*` in both the public JSON and the R + Python clients (`config.py`, `utils.R`, plus their tests). Dev bucket `bedrock-bio-genetics-dev` at `data-dev.bedrock.bio` provisioned alongside.
- **2026-05-21** — Cloudflare zone hardening applied via `bedrock-bio-infra/infra/networking/cloudflare.tf`:
  - **Rate limiting** (the Queued item): one zone-wide rule on `mcp.bedrock.bio/mcp*` + `mcp-dev.bedrock.bio/mcp*`, 50 req per 10s per IP per colo, 10s cool-off. Free plan locks `period`, `mitigation_timeout`, and includes `cf.colo.id` as a required characteristic — effective protection is throttling, not blocking. Pro plan unlocks proper block durations.
  - **Bot blocking**: zone-wide custom UA list (~60 entries: AI training crawlers, SEO scrapers, content scrapers, social card preview crawlers except LinkedInBot, Internet Archive). Stacks with Cloudflare's managed AI Scrapers list (`ai_bots_protection = "block"`) and AI Labyrinth (`crawler_protection = "enabled"`). Search engines (Googlebot, Bingbot, DuckDuckBot) intentionally allowed.
  - **Managed robots.txt** with Content Signals: `search=yes, ai-train=no` (dashboard-only, no Terraform resource exists).
  - **Bot Fight Mode** (`fight_mode = true`) + JS detections (`enable_js = true`) for baseline automated-traffic detection.
  - **SSL/TLS**: Full Strict, Always Use HTTPS, Automatic HTTPS Rewrites, Min TLS 1.2, HSTS (1yr, no `includeSubDomains`) via `add_security_headers` managed transform.
  - **DNSSEC** active; **Zone Hold** against accidental zone takeover.
  - **Tiered Cache** (Smart) on; reduces R2 origin pulls for `data.bedrock.bio`.
  - **CAA records** restricting cert issuance to `pki.goog`, `letsencrypt.org`, `digicert.com`, `amazon.com`; `iodef` reports to `liam@bedrock.bio`.
  - **Web Analytics** (privacy-respecting RUM) auto-installed on `bedrock.bio`.
  - **Cache ruleset** on `data.bedrock.bio` + `data-dev.bedrock.bio` with 1-year edge TTL.
  - Decided against rate-limiting `data.bedrock.bio` (R2 egress is free; static JSON is edge-cached; bulk download is already possible via the published `credentials.json` S3 keys, so HTTP rate limit would be theater).

## Pending release

Merged to `main` and live on dev (`mcp-dev.bedrock.bio`), but won't reach prod until the next GitHub release. The same release event publishes the MCP worker, the Python package, and the R client — releases are batched (see "Release cadence" below).

- Dev/prod environment split
- Phase 1 observability
- Workflow-injected `ACCOUNT_ID` / `R2_BUCKET_NAME` + single-bucket consolidation

## In progress

(none — Phase 1 complete on dev)

## Queued

### Phase 2: Analytics Engine
Builds on Phase 1's `logEvent()`. Adds an AE binding and extends the helper to dual-write (`console.log` + `writeDataPoint`). Refactor SQL parser to expose `extractTableRefs()` so aggregation by namespace/table is queryable. Enables SQL-queryable metrics for query volume, hot namespaces/tables, error rates, R2 SQL p95 latency.

Open schema decisions deferred to phase 2:
- Single shared AE dataset with an `environment` blob (preferred) vs. separate `mcp_events_dev` / `mcp_events_prod` datasets
- Log the SQL `text` or only a `sql_hash` for grouping

### User-facing docs + discoverability
- Section in `bedrock-bio-www` showing how to connect Claude Desktop / Claude Code / Cursor to the MCP server
- Submit to public MCP registry at `github.com/modelcontextprotocol/servers`

## Deferred (revisit when justified)

- **Uptime monitoring on `/health`** — external check + alerting. Revisit when first paying customer signs, or when going on vacation. Cloudflare Health Checks is the cleanest fit (already in stack) but Pro plan only ($240/yr); not worth it for zero-external-user state. Free-tier alternatives (Better Uptime, UptimeRobot, GitHub Actions cron) explicitly declined to avoid adding a third-party vendor.
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
- **Future bucket rename** (whenever `bedrock-bio-genetics` → more general name happens): `aws s3 sync` old → new bucket, re-register R2 Data Catalog on the new bucket (regenerates `metadata_json` paths in the manifest on Dagster's next publish), rotate `mcp-r2-sql-ro-prod` token to the new bucket scope, flip the `R2_BUCKET_NAME` repo variable and redeploy MCP, re-point `data.bedrock.bio`.
- **Cloudflare Pro upgrade triggers** (currently on Free, $240/yr blocker): paying customer signs (uptime/duty-of-care), MCP traffic exceeds Free 1-rate-limit-rule capacity, vacation (need real uptime monitoring), or real bot abuse incident that the custom list misses. Pro unlocks WAF Managed Rulesets (OWASP), real rate-limit `mitigation_timeout`, Cloudflare Health Checks (10 endpoints, alerting), Super Bot Fight Mode.
