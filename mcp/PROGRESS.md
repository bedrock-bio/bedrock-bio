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
- **2026-05-20** — Revoked old over-scoped Cloudflare API token; replaced with `mcp-r2-rw-prod` (R2 Admin Read & Write). Token must be created from the R2 page (not generic API Tokens) — see [reference_r2_sql_token](../../.agents/claude/projects/-Users-labbott-Repositories-bedrock-bio-client/memory/reference_r2_sql_token.md). Originally created as `mcp-r2-sql-ro-prod` with the generic "Workers R2 SQL Read" permission, which silently 401s against R2 SQL; renamed and re-scoped 2026-05-22 once R2 SQL was first exercised end-to-end. `mcp-r2-rw-dev` added the same day.
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
  - **Bot Fight Mode disabled** (`fight_mode = false`, `enable_js = false`). Briefly enabled the same day, then rolled back after BFM Managed-Challenged libcurl/R clients on Azure GitHub Actions IPs, breaking `r-check` CI on `data.bedrock.bio` (Python urllib unaffected — different TLS/JA3 fingerprint). Free-tier BFM is not skippable via Custom Rules; the `phases = ["http_request_sbfm"]` Skip action only bypasses Pro+ SBFM, and silently no-ops on Free (confirmed against Security Events). On Free, BFM is zone-wide on/off; the actual bot threat is already covered by `ai_bots_protection`, `crawler_protection`, the custom UA blocklist, and the `/mcp` rate limit. Revisit when on Pro (SBFM is per-hostname-skippable).
  - **SSL/TLS**: Full Strict, Always Use HTTPS, Automatic HTTPS Rewrites, Min TLS 1.2, HSTS (1yr, no `includeSubDomains`) via `add_security_headers` managed transform.
  - **DNSSEC** active; **Zone Hold** against accidental zone takeover.
  - **Tiered Cache** (Smart) on; reduces R2 origin pulls for `data.bedrock.bio`.
  - **CAA records** restricting cert issuance to `pki.goog`, `letsencrypt.org`, `digicert.com`, `amazon.com`; `iodef` reports to `liam@bedrock.bio`.
  - **Web Analytics** (privacy-respecting RUM) auto-installed on `bedrock.bio`.
  - **Cache ruleset** on `data.bedrock.bio` + `data-dev.bedrock.bio` with 1-year edge TTL.
  - Decided against rate-limiting `data.bedrock.bio` (R2 egress is free; static JSON is edge-cached; bulk download is already possible via the published `credentials.json` S3 keys, so HTTP rate limit would be theater).
- **2026-05-22** — Phase 2 Step 1 (PR #26): `analytics_engine_datasets` binding `MCP_EVENTS` → `bedrock_bio_mcp_events` (prod) / `bedrock_bio_mcp_events_dev` (dev). Nothing writes yet. Also: DO binding renamed `MCP_OBJECT` → `MCP_SERVER` (label only); README staleness pass.
- **2026-05-22** — Phase 2 Step 2 (PR #27): `extractTableRefs` extracted from `catalog.ts`, now walks `JOIN` as well as `FROM`. Closes a latent bug where JOIN'd partitioned tables bypassed partition-filter validation. `findMissingPartitionFilters` is now a thin wrapper.
- **2026-05-22** — Phase 2 Step 3: `logEvent(env, event)` dual-writes to `console.log` (unchanged) and `MCP_EVENTS.writeDataPoint(...)`. Blob/double/index positions pinned in a header comment in `log.ts` (reordering would break saved AE SQL queries). `sql_hash` computed via FNV-1a 32-bit doubled → 16 hex chars; auto-derived from `sql` if not caller-supplied. AE writes are try/catch'd with `console.warn` on failure — never breaks a tool call. `MCP_EVENTS` reached via `Cloudflare.Env` (wrangler-generated). New `src/log.test.ts` (11 tests) covers hash determinism, positional shape, default-fill, caller-supplied hash, no-binding back-compat, and writeDataPoint-throws safety.
- **2026-05-22** — First end-to-end `query` success on dev verified via MCP Inspector (`outcome: ok`, `r2_sql_status: 200`, `r2_sql_ms ~900ms`). Path had two latent bugs blocking it since the May-20 changes; both fixed today:
  - **Empty bucket var.** Both deploy workflows referenced `${{ vars.R2_BUCKET_NAME }}` but the GitHub repo variable was named `CLOUDFLARE_R2_BUCKET`, so `R2_BUCKET_NAME` expanded to `""` on every deploy. Symptom: `R2 SQL HTTP 404: Route not found.` from a malformed URL (`.../r2-sql/query/`). Fix: renamed GitHub variable to `R2_BUCKET_NAME` (workflow files unchanged). Worker now receives `R2_BUCKET_NAME=bedrock-bio-genetics`.
  - **Wrong token type.** Both `R2_SQL_TOKEN` Worker secrets were generic Cloudflare API tokens with the `Workers R2 SQL: Read` permission (from My Profile → API Tokens). That permission row exists but silently 401s against the R2 SQL service. R2 SQL needs an **R2 API token** created from R2 → Manage API tokens, with **Admin Read & Write** (verified empirically — `Admin Read only` also 401s, despite docs claiming it suffices for Data Catalog). Tokens renamed `mcp-r2-rw-{dev,prod}` to reflect actual scope; saved in `reference_r2_sql_token` memory.
  - **Deferred wash:** the earlier `warehouse` field added to the R2 SQL request body (mirroring wrangler's CLI shape) was reverted — URL routing alone is sufficient once the bucket name is non-empty.
- **2026-05-22** — Prod token rotation pending. `mcp-r2-rw-prod` is in place but the prod query path has never been exercised end-to-end. Verify before/during the next batched release.

## Pending release

Merged to `main` and live on dev (`mcp-dev.bedrock.bio`), but won't reach prod until the next GitHub release. The same release event publishes the MCP worker, the Python package, and the R client — releases are batched (see "Release cadence" below).

- Dev/prod environment split
- Phase 1 observability
- Workflow-injected `ACCOUNT_ID` / `R2_BUCKET_NAME` + single-bucket consolidation
- Phase 2 Steps 1–3 (AE binding + `extractTableRefs` refactor + dual-write `logEvent`)

## In progress

Phase 2 (Analytics Engine) — Steps 4–6 (see Queued).

## Queued

### Phase 2: Analytics Engine
Builds on Phase 1's `logEvent()`. Adds an AE binding and extends the helper to dual-write (`console.log` + `writeDataPoint`). Refactor SQL parser to expose `extractTableRefs()` so aggregation by namespace/table is queryable. Enables SQL-queryable metrics for query volume, hot namespaces/tables, error rates, R2 SQL p95 latency.

Workers Logs (Phase 1) stays as-is for per-event ops debugging (~24h–7d retention, dashboard/`wrangler tail` only). AE is the analytics layer (90d retention, SQL via HTTPS API). Same `logEvent()` helper fans out to both.

Resolved schema decisions:
- **Datasets**: two, same binding name `MCP_EVENTS`, different dataset per env — `bedrock_bio_mcp_events` (prod, the analytics source of truth) and `bedrock_bio_mcp_events_dev` (dev, write-only, exists to validate the AE write path on every deploy; never queried for analytics). Rationale: AE is product analytics, not ops correlation, so cross-env queries aren't useful; dataset-name-as-env-filter avoids "forgot the WHERE environment=…" footguns; account-namespaced prefix matches the rest of the infra and avoids future collisions. `writeDataPoint` is fire-and-forget with no ack, so dev writes are the only way to verify wiring end-to-end before promoting.
- **SQL logging**: log both full `sql` text (blob, for drill-down) and `sql_hash` (FNV-1a, 16 hex, blob, for `GROUP BY` on recurring query patterns). AE's 90d retention exceeds Workers Logs', so AE becomes the long-tail record of query text.
- **No `environment` blob** — dataset name carries the distinction. Frees a blob slot.

AE event shape (tentative — finalize during Step 3):
- `blobs`: `event_type`, `tool`, `outcome`, `version`, `sql_hash`, `sql`, `namespace`, `table`
- `doubles`: `duration_ms`, `r2_sql_ms`, `r2_sql_status`, `rows_returned`, `rows_total`
- `indexes`: `tool` (sampling key — low-cardinality, 3 values today)
- For `query` events touching multiple tables: emit one base event + one child row per referenced table (same `sql_hash` as foreign key, `namespace`/`table` populated only on children) to make `GROUP BY namespace, table` trivial.

Step-by-step:
1. ✅ Add `analytics_engine_datasets` binding to `wrangler.jsonc`.
2. ✅ Refactor `catalog.ts` to expose `extractTableRefs(sql)`; expand to walk `JOIN` as well as `FROM`.
3. ✅ Extend `logEvent()` to accept the AE binding and dual-write. `console.log` path unchanged in both envs.
4. Per-table fan-out for `query` events.
5. Add `mcp/scripts/ae-query.sh` (or `.ts`) wrapping `POST .../analytics_engine/sql` with a new narrow-scoped token (Account Analytics:Read — not reusing `mcp-r2-sql-ro-prod`). Bundle ~5 canned queries: daily volume by tool, top namespaces/tables, outcome breakdown, p50/p95/p99 of `duration_ms` + `r2_sql_ms`, top `sql_hash`es.
6. Deploy to dev, generate events via MCP Inspector, verify shape by querying `bedrock_bio_mcp_events_dev`. Then promote in the next batched release.

Risks to confirm before starting:
- AE Free-tier write/query quotas (10M writes/day, 10K queries/day account-wide) — well above current traffic but verify the account is on Workers Free, not Bundled.
- No PII in `sql` blob today (user-authored read-only queries against public bio data). Revisit if auth + per-user identifiers ever land.

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
