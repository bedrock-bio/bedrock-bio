
# bedrock-bio

Open-Access Computational Biology Datasets

## Description

Efficiently access a curated library of open-access computational biology
datasets. Tables support predicate pushdown and projection to the cloud
storage backend, enabling quick, iterative access to otherwise massive,
unwieldy tables.

`bedrock_bio` consists of five user-facing functions:

- `list_namespaces()`: returns a list of available namespace (data source)
  identifiers
- `describe_namespace('<name>')`: returns metadata, citation, license,
  instructions, and the tables for a namespace
- `list_tables()`: returns a list of available table identifiers
- `describe_table('<name>')`: returns metadata, citation, partition and sort
  keys, and column definitions for a table
- `load_table('<name>')`: returns a lazy DuckDB relation for a table

DuckDB methods (`filter`, `select`, `limit`) can be used on the relation
returned by `load_table` to push down row filters and column selections to
the storage backend. Filtering on the partition columns returned by
`describe_table` gives the fastest reads.

## Installation

To install the latest release from [PyPI](https://pypi.org/project/bedrock_bio/):

```bash
pip install bedrock-bio
```

Or install the current development version from
[GitHub](https://github.com/bedrock-bio/bedrock-bio-client):

```bash
pip install git+https://github.com/bedrock-bio/bedrock-bio-client.git@main#subdirectory=python
```

## Examples

```python
import bedrock_bio as bb
```

List available tables:

```python
bb.list_tables()
```

Describe a table to see its metadata, citation, and columns:

```python
bb.describe_table('ukb_ppp.pqtls')
```

Lazily load a table, filter on partition columns (for fastest reads), select
columns, and collect into an in-memory data frame:

```python
df = (
    bb.load_table('ukb_ppp.pqtls')
      .filter("ancestry = 'EUR' AND protein_id = 'A0FGR8' AND panel = 'Inflammation'")
      .select('chromosome, position, effect_allele, other_allele, beta, neg_log_10_p_value')
      .df()
)
```

## Dataset Requests

To request the addition of a new table to the library, open an
[issue](https://github.com/bedrock-bio/bedrock-bio-client/issues).
