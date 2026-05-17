
# bedrockbio

Open-Access Computational Biology Datasets

## Description

Efficiently access a curated library of open-access computational biology
datasets. Tables support predicate pushdown and projection to the cloud
storage backend, enabling quick, iterative access to otherwise massive,
unwieldy tables.

`bedrockbio` consists of three user-facing functions:

- `list_tables()`: returns a character vector of available table identifiers
- `describe_table("<name>")`: returns metadata, citation, and column
  definitions for a table
- `load_table("<name>", ...)`: takes a table name and optional partition
  filters, and returns a lazily-evaluated data frame

`dplyr` verbs (`filter`, `select`) can be used on the data frame returned by
`load_table` to push down additional row filters and column selections to the
storage backend.

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

Lazily load a table (optionally with partition filters for partitioned tables), 
select columns, and collect the relevant subset into an in-memory data frame:

```r
df <- load_table(
  "ukb_ppp.pqtls",
  ancestry = "EUR",
  protein_id = "A0FGR8",
  panel = "Inflammation"
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
