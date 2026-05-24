## R CMD check results

0 errors | 0 warnings | 0 notes

* This release adds `list_namespaces()` and `describe_namespace()` for
  discovering and inspecting data sources. See `NEWS.md` for details.
* OS_type: unix — the DuckDB iceberg extension is not available for
  Windows (R on Windows uses MinGW, and the iceberg extension has no
  MinGW build). See https://github.com/duckdb/duckdb-iceberg for
  upstream status.
* Examples are wrapped in \dontrun{} because they require network
  access that is not available on the CRAN build farm.

## Test environments

* local macOS (aarch64-apple-darwin), R 4.5.2
* GitHub Actions macOS-latest, R 4.5
* GitHub Actions ubuntu-latest, R 4.5
* GitHub Actions ubuntu-latest, R 4.4
* GitHub Actions ubuntu-latest, R 4.3
* GitHub Actions ubuntu-latest, R 4.2
* GitHub Actions ubuntu-latest, R 4.1
