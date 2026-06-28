
# bedrockbio

Open-Access Computational Biology Datasets

## Description

Efficiently access a curated library of open-access computational biology
datasets. Tables support predicate pushdown and projection to the cloud
storage backend, enabling quick, iterative access to otherwise massive,
unwieldy tables.

`bedrockbio` consists of six user-facing functions:

- `list_namespaces()`: returns a character vector of available namespace
  (data source) identifiers
- `describe_namespace("<name>")`: returns a namespace's name, citation,
  license, context, and its tables
- `list_tables(namespace)`: returns a character vector of table identifiers,
  optionally filtered to one namespace
- `describe_table("<name>")`: returns a table's context, column definitions,
  and partition columns (with their allowed values)
- `load_table("<name>")`: returns a lazily-evaluated data frame for a table
- `reset()`: clears cached state (manifest, namespaces, connection)

`dplyr` verbs (`filter`, `select`) can be used on the data frame returned by
`load_table` to push down row filters and column selections to the storage
backend. Filtering on the partition columns returned by `describe_table`
gives the fastest reads.

## Installation

Install from [CRAN](https://cran.r-project.org/):

```r
install.packages("bedrockbio")
```

Or install the current development version from
[GitHub](https://github.com/bedrock-bio/bedrock-bio-client):

```r
# install.packages("pak")
pak::pak("bedrock-bio/bedrock-bio-client/r")
```

The R package supports macOS and Linux only: the DuckDB `iceberg` extension
has no MinGW build, so it cannot load on R for Windows. Windows users can use
the [Python client](https://pypi.org/project/bedrock-bio/) instead, which works
on all platforms.

## Examples

Load the package (and `dplyr` for downstream data frame manipulation):

```r
library(bedrockbio)
library(dplyr)
```

List available tables:

```r
list_tables()
```

Describe a table to see its metadata, citation, and columns:

```r
describe_table("ukb_ppp.pqtls")
```

Lazily load a table, filter on partition columns (for fastest reads), select
columns, and collect the relevant subset into an in-memory data frame:

```r
df <- load_table("ukb_ppp.pqtls") |>
  filter(
    ancestry == "EUR",
    protein_id == "A0FGR8",
    panel == "Inflammation"
  ) |>
  select(
    chromosome,
    position,
    effect_allele,
    other_allele,
    beta,
    neg_log_10_p_value
  ) |>
  collect()
```

## Dataset Requests

To request the addition of a new table to the library, open an
[issue](https://github.com/bedrock-bio/bedrock-bio-client/issues).
