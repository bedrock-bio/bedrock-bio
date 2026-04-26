# bedrockbio 1.3.0

* Initial CRAN submission.
* `list_tables()`: list available tables.
* `load_table()`: lazily query a table with required partition filters and
  predicate pushdown via 'DuckDB' and 'Apache Iceberg'.
* `describe_table()`: view table metadata, citation, and column definitions.
