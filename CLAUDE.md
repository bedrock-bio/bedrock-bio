# Bedrock Bio Client

This monorepo holds user-facing access methods for Bedrock Bio data, one per top-level subdirectory:

- `r/` — R client package
- `python/` — Python client package
- `mcp/` — Cloudflare Worker MCP server (added May 2026 by migrating the standalone `bedrock-bio-mcp` repository into this monorepo; the original repo has been archived)

All three consume the same `manifest.json` catalog produced by the bedrock-bio-dagster pipeline; that JSON schema is the cross-cutting contract. Each subdirectory is self-contained with its own toolchain — operate from inside the subdir for target-specific commands.

CI workflows are split per-target (`mcp-*.yml`, `python-*.yml`, `r-*.yml`); changes to one subdirectory don't trigger checks for the others.
