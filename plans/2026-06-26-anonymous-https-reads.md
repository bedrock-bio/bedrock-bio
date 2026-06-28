# Anonymous HTTPS reads — drop R2 credentials from the clients

**Goal:** Make the R and Python clients read Iceberg tables **anonymously over the public
custom domains** instead of authenticating with R2 S3 credentials. After this change the
clients fetch `manifest.json`, get each table's `s3://<bucket>/…metadata.json` path, and
let DuckDB resolve it to `https://<bucket>.bedrock.bio/…` with **no access keys, no S3 API,
no `credentials.json`**.

**Why this works (already proven).** Cloudflare R2 buckets are now public behind custom
domains (`data.bedrock.bio`, `data-dev.bedrock.bio`, `bedrock-bio-data.bedrock.bio`,
`bedrock-bio-data-dev.bedrock.bio`) with a Cache-Everything rule (done in
`bedrock-bio-infra`). DuckDB's `iceberg_scan` reads the metadata tree
(`metadata.json → manifest-list → manifests`) and the data parquet entirely over httpfs;
the Iceberg manifests enumerate every file and carry per-file column bounds, so partition
pruning and predicate pushdown work over plain HTTPS with zero credentials. The only thing
that changes is **how DuckDB resolves the `s3://` paths**: today via the authenticated R2
S3 endpoint, after this via the public custom domain in vhost style. Verified empirically:
anonymous `iceberg_scan` returned correct rows with `duckdb_secrets()` empty and the
partition filter pushed into `ICEBERG_SCAN`.

**Scope.** This is the *only* repo that changes. The Dagster repo emits the same `s3://`
`metadata_json` it always has (no change); the MCP server uses R2 SQL, not DuckDB (no
change); infra is merged. `credentials.json` is still served by infra and is now unused —
retiring it is a separate, later infra task, not part of this plan.

**Resolution mechanism.** DuckDB vhost-style maps `s3://<bucket>/<key>` →
`https://<bucket>.<s3_endpoint>/<key>`. With `s3_endpoint = 'bedrock.bio'`:
- prod: `s3://bedrock-bio-data/…` → `https://bedrock-bio-data.bedrock.bio/…`
- dev: `s3://bedrock-bio-data-dev/…` → `https://bedrock-bio-data-dev.bedrock.bio/…`

Both custom domains are bound to their buckets, so the constructed URL resolves. The
`s3_endpoint` is constant across envs (the bucket name comes from the `metadata_json` path
itself), so the client needs no per-env bucket mapping.

---

## Task 0: Validation gate (no code change — do this first)

Prove the anonymous read works against **dev** before touching any client code, using the
DuckDB version the clients actually pin. If this fails, stop — it's an infra/domain issue,
not a client-code issue, and shipping the code change would break the clients.

- [ ] **Confirm the dev anonymous vhost read**

```bash
META=$(curl -s https://data-dev.bedrock.bio/manifest.json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); ns=d['namespaces']['dbsnp']['tables']['vcf']; print(ns['metadata_json'])")
echo "metadata_json: $META"   # expect s3://bedrock-bio-data-dev/...

duckdb -c "
INSTALL httpfs; LOAD httpfs; INSTALL iceberg; LOAD iceberg;
SET s3_endpoint='bedrock.bio'; SET s3_url_style='vhost'; SET s3_use_ssl=true; SET s3_region='auto';
SELECT * FROM duckdb_secrets();                                   -- expect ZERO rows (anonymous)
SELECT count(*) FROM iceberg_scan('$META') WHERE chromosome='22'; -- expect a count, no auth error
EXPLAIN SELECT * FROM iceberg_scan('$META') WHERE chromosome='22';-- expect ICEBERG_SCAN + pushed filter
"
```

Confirm: rows return, `duckdb_secrets()` is empty, and it reads R2's **gzipped**
`*.gz.metadata.json` natively (R2 Data Catalog gzips metadata; this is the one thing the
local proof didn't exercise). If the gzip read is the only failure, that's a real blocker —
flag it before proceeding.

- [ ] **Confirm the pinned client DuckDB version behaves the same**

Run the same `SET`-based anonymous scan under the DuckDB version in `python/uv.lock` (and
the R `duckdb` package version). The `SET s3_*` legacy mechanism is broadly stable across
versions, but verify rather than assume. If `SET`-only anonymous reads misbehave on the
pinned version, use the scoped-secret fallback documented in Task 1.

---

## Task 1: Python client — switch `get_connection` to anonymous, remove credentials machinery

**File:** `python/src/bedrock_bio/config.py`

- [ ] **Rewrite `get_connection()`** (currently lines ~110-125)

Replace:

```python
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        if self.conn is not None:
            return self.conn

        credentials = self.get_credentials()
        self.conn = duckdb.connect()
        self.conn.sql("INSTALL httpfs")
        self.conn.sql("INSTALL iceberg")
        self.conn.execute(
            "CREATE SECRET (TYPE s3, KEY_ID ?, SECRET ?, ENDPOINT ?, URL_STYLE 'path')",
            [
                credentials["R2_ACCESS_KEY_ID"],
                credentials["R2_SECRET_ACCESS_KEY"],
                f"{credentials['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            ],
        )
        return self.conn
```

with:

```python
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        if self.conn is not None:
            return self.conn

        self.conn = duckdb.connect()
        self.conn.sql("INSTALL httpfs")
        self.conn.sql("INSTALL iceberg")
        # Anonymous, cache-fronted reads over the public custom domain. Each
        # table's metadata_json is s3://<bucket>/...; vhost resolution maps it to
        # https://<bucket>.bedrock.bio/... — no credentials, no S3 API, no listing.
        # The connection is private to this package, so global SET is safe here.
        self.conn.sql("SET s3_endpoint='bedrock.bio'")
        self.conn.sql("SET s3_url_style='vhost'")
        self.conn.sql("SET s3_use_ssl=true")
        self.conn.sql("SET s3_region='auto'")
        return self.conn
```

- [ ] **Delete the dead credentials machinery:**
  - the `credentials: dict[str, str] | None = None` dataclass field (line ~15)
  - the `credentials_url` property (lines ~29-31)
  - the entire `get_credentials()` method (lines ~92-108)
  - in `reset()`, the `self.credentials = None` line
  - the comment "Bound network stalls on the manifest/credentials fetches" → drop
    "/credentials"

- [ ] **Update `reset.py` docstring** — remove the "credentials" mentions; `reset()` now
  clears the manifest/namespaces cache and the connection (useful when the manifest changes
  or `BB_ENV` changes mid-session), not credentials.

**Fallback (only if Task 0 showed `SET`-only anonymous fails on the pinned DuckDB):** use a
scoped empty-credential secret instead of the `SET` block. It needs the bucket name, so add
a `bucket` property keyed off `BB_ENV` (mirroring `base_url`: prod `bedrock-bio-data`, dev
`bedrock-bio-data-dev`) and:

```python
        self.conn.execute(
            "CREATE SECRET (TYPE s3, SCOPE ?, ENDPOINT 'bedrock.bio', "
            "URL_STYLE 'vhost', USE_SSL true, REGION 'auto', KEY_ID '', SECRET '')",
            [f"s3://{self.bucket}/"],  # trailing slash so prod scope ≠ dev prefix
        )
```

---

## Task 2: Python tests

**File:** `python/tests/test_config.py`

- [ ] **Delete** the three credentials tests: `test_credentials_returns_expected_keys`,
  `test_credentials_caches_result`, `test_credentials_errors_when_url_unreachable`.

- [ ] **Rewrite** `test_connection_returns_duckdb_with_s3_secret` → it no longer creates a
  secret:

```python
    def test_connection_uses_anonymous_vhost(self):
        conn = config.get_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        # No secret — reads are anonymous over the public custom domain.
        assert conn.sql("FROM duckdb_secrets()").fetchall() == []
        assert conn.sql("SELECT current_setting('s3_endpoint')").fetchone()[0] == "bedrock.bio"
        assert conn.sql("SELECT current_setting('s3_url_style')").fetchone()[0] == "vhost"
```

  Keep `test_connection_caches` unchanged.

**File:** `python/tests/test_env.py`

- [ ] **Delete** both `config.credentials_url == …` assertions (the property is gone). The
  `base_url` / `manifest_url` assertions stay.

**File:** `python/tests/test_reset.py`

- [ ] In `test_reset_clears_state`, **delete** the `config.credentials = {…}` setup line and
  the `assert config.credentials is None` line.

- [ ] **Run:** `cd python && uv run pytest -q`. Expect green, including
  `test_load_table.py` (the live anonymous `iceberg_scan` end-to-end — the real proof).

---

## Task 3: R client — same change

**File:** `r/R/utils.R`

- [ ] **Rewrite `get_connection()`** (currently lines ~99-118):

```r
get_connection <- function() {
  if (!is.null(pkg$conn)) {
    return(pkg$conn)
  }

  pkg$conn <- DBI::dbConnect(duckdb::duckdb())
  DBI::dbExecute(pkg$conn, "INSTALL httpfs")
  DBI::dbExecute(pkg$conn, "INSTALL iceberg")
  # Anonymous, cache-fronted reads over the public custom domain. metadata_json
  # is s3://<bucket>/...; vhost maps it to https://<bucket>.bedrock.bio/... —
  # no credentials, no S3 API. The connection is private to this package.
  DBI::dbExecute(pkg$conn, "SET s3_endpoint='bedrock.bio'")
  DBI::dbExecute(pkg$conn, "SET s3_url_style='vhost'")
  DBI::dbExecute(pkg$conn, "SET s3_use_ssl=true")
  DBI::dbExecute(pkg$conn, "SET s3_region='auto'")

  pkg$conn
}
```

- [ ] **Delete** the entire `get_credentials()` function (lines ~81-96) and drop "/credentials"
  from the comment on line ~4.

**File:** `r/R/zzz.R`

- [ ] In `set_host_urls()`, **delete** the `pkg$credentials_url <- paste0(host, "/credentials.json")`
  line.

**File:** `r/R/reset.R`

- [ ] **Delete** `pkg$credentials <- NULL`; update the roxygen docstring to drop "credentials"
  (reset clears the manifest/namespaces cache + connection; useful on manifest change or
  `BB_ENV` change).

---

## Task 4: R tests

**File:** `r/tests/testthat/test-utils.R`

- [ ] **Delete** the three `get_credentials` tests (the `# --- get_credentials ---` block:
  returns-keys, caches, errors-when-unreachable).

- [ ] **Rewrite** `get_connection returns DuckDB with S3 secret` → no secret now:

```r
test_that("get_connection uses anonymous vhost settings", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  conn <- bedrockbio:::get_connection()
  expect_s4_class(conn, "duckdb_connection")
  secrets <- DBI::dbGetQuery(conn, "FROM duckdb_secrets()")
  expect_equal(nrow(secrets), 0L)
  endpoint <- DBI::dbGetQuery(conn, "SELECT current_setting('s3_endpoint') AS v")$v
  expect_equal(endpoint, "bedrock.bio")
})
```

  Keep `get_connection caches`.

**File:** `r/tests/testthat/test-env.R`

- [ ] **Delete** the two `expect_equal(pkg$credentials_url, …)` assertions (prod + dev tests).
  Keep the `manifest_url` assertions.

**File:** `r/tests/testthat/test-reset.R`

- [ ] In `reset clears cached state`, **delete** `pkg$credentials <- list(R2_ACCESS_KEY_ID = "x")`
  and `expect_null(pkg$credentials)`.

- [ ] **Run:** `cd r && Rscript -e 'devtools::test()'` (or `R CMD check`). Expect green,
  including `test-load_table.R` (the live anonymous read).

---

## Task 5: Version bump + changelog

- [ ] **Python:** bump `python/pyproject.toml` `version = "1.4.1"` → `"1.5.0"`; add to
  `python/CHANGELOG.md`:

```markdown
## bedrock-bio 1.5.0

* Reads are now anonymous over HTTPS — the client no longer fetches `credentials.json`
  or creates an R2 S3 secret. No API keys are required. Partition pruning and predicate
  pushdown are unchanged.
```

- [ ] **R:** bump `r/DESCRIPTION` `Version: 1.4.1` → `1.5.0`; add the matching entry to
  `r/NEWS.md`.

- [ ] **Check READMEs** (`python/README.md`, `r/README.md`) for any mention of credentials
  or keys in install/usage — currently none, but confirm. Usage (`load_table`, etc.) is
  unchanged.

---

## Task 6: Final verification

- [ ] **Dev end-to-end (both clients):**
  - Python: `cd python && BB_ENV=dev uv run pytest -q`
  - R: `cd r && BB_ENV=dev Rscript -e 'devtools::test()'`
  Both should read `dbsnp.vcf` anonymously and pass.

- [ ] **Prod smoke (no BB_ENV):** in each client, `load_table("dbsnp.vcf")` filtered to a
  partition returns rows, and a fresh process holds **no** R2 credentials anywhere.

- [ ] **Confirm full anonymity:** in a connection from the package, `FROM duckdb_secrets()`
  is empty and reads still succeed — proving no credential path remains.

---

## Out of scope / follow-ups

- **Retire `credentials.json` + the public read-only R2 token** (infra). Safe only after
  both clients ship 1.5.0 and old client versions are no longer in use — old clients still
  fetch `credentials.json` on startup and would break if it 404s. Keep serving it until
  then; it's harmless and unused by the new clients.
- **Parquet write-once invariant** (Dagster): the 1-year Cache-Everything TTL on the data
  domains is safe only if a re-sync never overwrites a parquet file at the same key. Iceberg
  metadata files are version-stamped (safe). Confirm the `PolarsR2IOManager` writes new
  filenames rather than overwriting partition files in place; if it can overwrite, shorten
  the parquet TTL or use content/run-stamped names. (Tracked in the infra/Dagster repos, not
  here.)
- **Bucket rename to `data` / `data-dev`** (future simplification): would collapse the data
  reads onto `data.bedrock.bio` directly (single domain, one cache, bucket name nowhere),
  but requires a bucket migration. Only pursue if the bucket-named data domain proves
  annoying in practice.
```
