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
