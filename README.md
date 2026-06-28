# bedrock-bio

Open-Access Computational Biology Datasets

## Description

Efficiently access a curated library of open-access computational biology 
datasets. Datasets support predicate pushdown and projection to the cloud 
storage backend, enabling quick, iterative access to otherwise massive, 
unwieldy datasets.

## Usage

This repository holds the **client libraries** for Bedrock Bio data:

- `r/` — R client package ([CRAN](https://cran.r-project.org/package=bedrockbio))
- `python/` — Python client package ([PyPI](https://pypi.org/project/bedrock-bio/))

The MCP server for LLM clients lives in its own repo,
[`bedrock-bio-mcp`](https://github.com/bedrock-bio/bedrock-bio-mcp) (hosted at
`https://mcp.bedrock.bio/mcp`). Both clients read the same `manifest.json` catalog.

See [bedrock.bio](https://bedrock.bio) for the dataset catalog, usage, and
guidance on choosing an access method.

## Dataset Requests

To request the addition of a new dataset to the library, open an
[issue](https://github.com/bedrock-bio/bedrock-bio-client/issues).
