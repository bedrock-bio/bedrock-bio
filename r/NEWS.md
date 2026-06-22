# bedrockbio 1.4.1

* `reset()`: now exported — clears the cached manifest, credentials, and
  connection (useful after credentials are rotated during a session).
* `BB_ENV=dev` points the client at the development data host
  (`data-dev.bedrock.bio`).
* Internal: timeouts on manifest and credentials requests.

# bedrockbio 1.4.0

* `list_namespaces()`: list available namespaces (data sources).
* `describe_namespace()`: view namespace metadata, citation, license,
  instructions, and the namespace's tables.

# bedrockbio 1.3.1

* Internal: hardened SQL string handling for catalog-derived paths and
  credentials.
* Internal: updated upstream manifest endpoint URL.

# bedrockbio 1.3.0

* Initial CRAN submission.
* `list_tables()`: list available tables.
* `load_table()`: lazily query a table with optional partition filters and
  predicate pushdown via 'DuckDB' and 'Apache Iceberg'.
* `describe_table()`: view table metadata, citation, and column definitions.
