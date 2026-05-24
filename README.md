# bedrock-bio

Open-Access Computational Biology Datasets

## Description

Efficiently access a curated library of open-access computational biology 
datasets. Datasets support predicate pushdown and projection to the cloud 
storage backend, enabling quick, iterative access to otherwise massive, 
unwieldy datasets.

## Usage

This monorepo holds three access methods, one per subdirectory:

- `r/` — R client package ([CRAN](https://cran.r-project.org/package=bedrockbio))
- `python/` — Python client package ([PyPI](https://pypi.org/project/bedrock-bio/))
- `mcp/` — MCP server for LLM clients, hosted at `https://mcp.bedrock.bio/mcp`

See [bedrock.bio](https://bedrock.bio) for the dataset catalog and full
documentation.

## Dataset Requests

To request the addition of a new dataset to the library, open an
[issue](https://github.com/bedrock-bio/bedrock-bio/issues).
