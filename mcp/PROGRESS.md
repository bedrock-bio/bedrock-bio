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
- **2026-05-20** — Revoked old over-scoped Cloudflare API token; replaced with `mcp-r2-rw-prod` (R2 Admin Read & Write). Token must be created from the R2 page (not generic API Tokens) — see [reference_r2_sql_token](../../.agents/claude/projects/-Users-labbott-Repositories-bedrock-bio/memory/reference_r2_sql_token.md). Originally created as `mcp-r2-sql-ro-prod` with the generic "Workers R2 SQL Read" permission, which silently 401s against R2 SQL; renamed and re-scoped 2026-05-22 once R2 SQL was first exercised end-to-end. `mcp-r2-rw-dev` added the same day.
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
- **2026-05-22** — Phase 2 Step 4: per-table fan-out for `query` events. `logEvent(env, event, tables?)` now emits one base AE row (empty `namespace`/`table`) plus one child row per `TableRef` from `extractTableRefs(sql)` when `tables` is passed — children share the base's `sql_hash` as the join key. Makes `GROUP BY namespace, table` trivial against the AE dataset. `console.log` stays one-line-per-call (Workers Logs is for ops debugging, not analytics) and includes a `tables: string[]` field (omitted when empty) for human reading. Internal `writeAE()` helper consolidates the positional schema in one place and returns a boolean so fan-out aborts after the first failure (one warn, no subsequent attempts). `list_tables` and `describe_namespace` call `logEvent` without `tables` — no fan-out path triggered. 5 new tests in `log.test.ts` cover N-table fan-out, zero-table base-only, console.log shape, no-binding back-compat, and first-write-failure abort.
- **2026-05-22** — Code hygiene pass folded into Step 4: dropped `Catalog.version`/`CatalogNamespace.id`/`CatalogTable.metadata_json` from the catalog types (none read by MCP — they describe the cross-cutting manifest schema, not MCP's view). Added private `refsFromStripped()` helper so `findMissingPartitionFilters` doesn't double-call `scrub` via `extractTableRefs`. Replaced the nested `try { try { } catch { } } catch { }` R2 SQL retry block with a 2-iteration `for` loop in `index.ts`. Added one-line comment explaining the SHOW/DESCRIBE/EXPLAIN early return in `findMissingPartitionFilters`.
- **2026-05-23** — Phase 2 Step 6: operational verification on dev. Fired four tool calls via MCP Inspector (`list_tables`, `describe_namespace`, single-table `query`, multi-table `JOIN` query against `ukb_ppp.pqtls` + `ukb_ppp.assays`); all returned `outcome: ok` with zero `AE write failed` warnings in `wrangler tail --env dev`. AE dashboard row counts on dev datasets matched the design: `mcp_calls_dev` = 4, `mcp_queries_dev` = 2 (correctly skipped on non-query tools), `mcp_tables_dev` = 3 (1 from the single-table query + 2 sharing one `call_id` from the JOIN — confirms `extractTableRefs` JOIN walk + fan-out). `mcp_sessions_dev` showed 6 rows vs 2 distinct tool-call-issuing `session_id`s — expected per `index.ts:58-62` (each MCP Inspector reconnect spawns a fresh DO; comment already flags "dedupe at query time"). Prod path still unverified end-to-end; first post-release `query` call will validate `mcp-r2-rw-prod` token + prod AE dataset population in one shot. Step 5 (canned `ae-query.sh` + bundled queries) intentionally deferred — the writes don't depend on it.
- **2026-05-22** — **Phase 2 schema rewrite**: superseded the single-dataset fan-out design with a four-dataset normalized schema. New datasets `mcp_sessions`, `mcp_calls`, `mcp_queries`, `mcp_tables` (dev `_dev`-suffixed). Bindings `MCP_SESSIONS`, `MCP_CALLS`, `MCP_QUERIES`, `MCP_TABLES`. Dropped the `bedrock_bio_` dataset prefix (account-scoped namespace is already unique). The single `mcp_events` dataset is abandoned in CF (no API to delete). Full analyst-facing schema lives in `mcp/SCHEMA.md`; positional schema enforced by typed tuples in `log.ts` (reorder breaks compile). Captured every R2 SQL response metric we previously dropped (`request_id`, `bytes_scanned`, `files_scanned`, `r2_requests_count`, error code). Added `cache_hit` (catalog cache outcome per call), `tool_args` (JSON of args for future polymorphism), `country`/`colo`/`user_agent` slots reserved on SESSIONS (currently empty — capturing them requires plumbing the HTTP request through the agents/mcp SDK lifecycle; tracked as a follow-up). `sql` truncated to 4900 chars for AE writes; `sql_hash` always over full text so pattern grouping stays correct. `logToolCall` orchestrator writes CALLS first then aborts on its failure (no orphan QUERIES/TABLES rows); TABLES loop tolerates partial failures. 15 tests in `log.test.ts` cover positional shapes, truncation, fan-out, abort-on-CALLS-failure, partial TABLES tolerance, console.log shape.
- **2026-05-23** — **Released v1.4.0** (MCP Worker + Python package + R client published in one batched release). Promoted the full "Pending release" bundle to prod: dev/prod environment split, Phase 1 observability, workflow-injected `ACCOUNT_ID`/`R2_BUCKET_NAME` + single-bucket consolidation, Phase 2 Steps 1–4 (AE bindings + `extractTableRefs` refactor + dual-write `logEvent` + four-dataset normalized schema), R2 SQL bucket-var + token-type bugfixes, code hygiene pass, and the new `mcp/SCHEMA.md` analyst doc. Pre-release audit (this session) caught and fixed: R lintr violations in the new `column_fields` constant, broken `load_table(..., **filters)` examples in both READMEs (API tightened to name-only this release), `describe_table` docstrings missing `partition_by`/`sort_by`, the still-says-"three"-functions blurb in both READMEs (now five), tracked `r.Rcheck/`/`..Rcheck/` artifacts, and a `zip(... _table ...)` smell in Python `_load_manifest`. R + Python clients also added `list_namespaces()` and `describe_namespace()` this release. Prod `/health` smoke-test green; prod `query` path + `mcp-r2-rw-prod` token + prod AE dataset population still need first end-to-end verification — fire one query via MCP Inspector against `mcp.bedrock.bio/mcp` to close that out.

## Pending release

_Nothing pending._ Everything that was queued in this section shipped with v1.4.0 on 2026-05-23.

## In progress

_Nothing in flight._ Phase 2 (Analytics Engine) operational verification complete on dev (2026-05-23) and shipped to prod with v1.4.0. Step 5 (canned query script) deferred until there's a reason to query the data.

## Queued

### Phase 2: Analytics Engine
Builds on Phase 1's `logEvent()`. Adds an AE binding and extends the helper to dual-write (`console.log` + `writeDataPoint`). Refactor SQL parser to expose `extractTableRefs()` so aggregation by namespace/table is queryable. Enables SQL-queryable metrics for query volume, hot namespaces/tables, error rates, R2 SQL p95 latency.

Workers Logs (Phase 1) stays as-is for per-event ops debugging (~24h–7d retention, dashboard/`wrangler tail` only). AE is the analytics layer (90d retention, SQL via HTTPS API). Same `logEvent()` helper fans out to both.

Resolved schema decisions (post-rewrite — see `mcp/SCHEMA.md` for the canonical column reference):
- **Four normalized datasets**: `mcp_sessions` (1 per MCP connection), `mcp_calls` (1 per tool invocation, universal fact table), `mcp_queries` (1 per `query`-tool call, type-specific extension), `mcp_tables` (1 per (call, distinct touched table), shared dimension). Each env gets its own `_dev`-suffixed copy (`mcp_sessions_dev`, etc.). Binding names are uppercase: `MCP_SESSIONS`, `MCP_CALLS`, `MCP_QUERIES`, `MCP_TABLES`. Rationale: normalization eliminates the sentinel-based `WHERE blob7=''` queries the prior fan-out design required, gives each dataset a uniform tight schema, and matches the polymorphic pattern that future tool types (e.g. methods on Modal) will extend by adding their own type-specific dataset analogous to `mcp_queries`. `mcp_tables` already generalizes to "tables referenced by any tool call," not just SQL queries.
- **No `bedrock_bio_` prefix on dataset names** — AE namespaces are per-account; the prefix was doubly-prefixed and redundant.
- **Positional schema enforced in code** via typed tuples in `log.ts` (`SessionsBlobs`, `CallsBlobs`, etc.). Reordering breaks compile; renaming is free. Analyst-facing doc in `mcp/SCHEMA.md` mirrors the same positions.
- **SQL truncation**: `sql` capped at 4900 chars for AE writes (UTF-8 headroom under the 5KB blob cap); `sql_hash` always computed over the full untruncated text so pattern grouping stays correct.
- **Single-dataset fan-out abandoned**: original PROGRESS.md design (one `mcp_events` dataset with a base-row + per-table-child fan-out keyed by `sql_hash`) was rewritten mid-Step-4 in favor of normalization. The `bedrock_bio_mcp_events` / `_dev` datasets in CF are stranded (no API to delete) but unused.

Step-by-step:
1. ✅ Add `analytics_engine_datasets` bindings to `wrangler.jsonc` (now four bindings per env).
2. ✅ Refactor `catalog.ts` to expose `extractTableRefs(sql)`; expand to walk `JOIN` as well as `FROM`.
3. ✅ Implement dual-write helpers (`logSession`, `logToolCall`) with `console.log` + per-dataset `writeDataPoint`.
4. ✅ Per-table fan-out for `query` events (now expressed as `mcp_tables` rows linked via `call_id`).
5. **Deferred** — `mcp/scripts/ae-query.sh` (or `.ts`) wrapping `POST .../analytics_engine/sql` with a narrow-scoped token (Account Analytics:Read), bundling canned queries from `mcp/SCHEMA.md`. Park until there's an actual reason to query the data; the writes don't depend on this existing.
6. ✅ Operational verification on dev (2026-05-23): all four tool paths landed `outcome: ok`, AE row counts matched (4 calls / 2 queries / 3 tables across two sessions' worth of activity), zero AE write warnings. Prod token (`mcp-r2-rw-prod`) verification rolls into the first prod query after the next batched release.

Risks to confirm before starting:
- **AE Free quotas**: 100K writes/day, 10K reads/day per account on Workers Free; 10M writes/month + 1M reads/month included on Workers Paid ($0.25/M and $1/M overage). At plausible early-stage traffic the four-dataset design generates ~100K writes/month — single-digit-percent of the Paid included allowance.
- **No PII in `sql` blob today** (user-authored read-only queries against public bio data). Revisit if auth + per-user identifiers ever land.
- **Follow-up: capture `country`/`colo`/`user_agent` on `mcp_sessions`** — slots reserved but populated empty today. Requires plumbing the HTTP request through the agents/mcp SDK's `setInitializeRequest` lifecycle (the DO doesn't see the original request at that hook). Track separately.

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
- **Future bucket rename** (whenever `bedrock-bio-genetics` → more general name happens): `aws s3 sync` old → new bucket, re-register R2 Data Catalog on the new bucket (regenerates `metadata_json` paths in the manifest on Dagster's next publish), rotate `mcp-r2-rw-prod` token to the new bucket scope, flip the `R2_BUCKET_NAME` repo variable and redeploy MCP, re-point `data.bedrock.bio`.
- **Cloudflare Pro upgrade triggers** (currently on Free, $240/yr blocker): paying customer signs (uptime/duty-of-care), MCP traffic exceeds Free 1-rate-limit-rule capacity, vacation (need real uptime monitoring), or real bot abuse incident that the custom list misses. Pro unlocks WAF Managed Rulesets (OWASP), real rate-limit `mitigation_timeout`, Cloudflare Health Checks (10 endpoints, alerting), Super Bot Fight Mode.
