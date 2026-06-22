# Bedrock Bio Client

This repo holds the user-facing client libraries for Bedrock Bio data, one per top-level subdirectory:

- `r/` — R client package
- `python/` — Python client package

The MCP server lives in its own repo (`bedrock-bio-mcp`) — it is a deployed Cloudflare Worker, not a published library, so it follows the one-repo-per-Worker pattern (alongside `bedrock-bio-registry`, `bedrock-bio-api`). Both clients consume the same `manifest.json` catalog produced by the bedrock-bio-dagster pipeline; that JSON schema is the cross-cutting contract. Each subdirectory is self-contained with its own toolchain — operate from inside the subdir for target-specific commands.

CI workflows are split per-target (`python-*.yml`, `r-*.yml`) plus the `credentials-publish-*.yml` workflows; changes to one subdirectory don't trigger checks for the others.
