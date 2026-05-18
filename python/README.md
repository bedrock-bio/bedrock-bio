
# bedrock-bio

Open-Access Computational Biology Datasets

## Description

Efficiently access a curated library of open-access computational biology
datasets. Tables support predicate pushdown and projection to the cloud
storage backend, enabling quick, iterative access to otherwise massive,
unwieldy tables.

`bedrock_bio` consists of three user-facing functions:

- `list_tables()`: returns a list of available table identifiers
- `describe_table('<name>')`: returns metadata, citation, and column
  definitions for a table
- `load_table('<name>', **filters)`: takes a table name and optional
  partition filters, and returns a lazy DuckDB relation

DuckDB methods (`filter`, `select`, `limit`) can be used on the relation
returned by `load_table` to push down additional row filters and column
selections to the storage backend.

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

Lazily load a table (optionally with partition filters for partitioned
tables), select columns, and collect into an in-memory data frame:

```python
df = bb.load_table('ukb_ppp.pqtls', ancestry='EUR', protein_id='A0FGR8', panel='Inflammation') \
  .select('chromosome, position, effect_allele, other_allele, beta, neg_log_10_p_value') \
  .fetchdf()
```

## Dataset Requests

To request the addition of a new table to the library, open an
[issue](https://github.com/bedrock-bio/bedrock-bio-client/issues).
