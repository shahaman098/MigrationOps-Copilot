# MCP Server

This server exposes MigrationOps Copilot's live health-check tools over the Model Context Protocol (MCP).

## Exposed Tools

- `check_ssl_certificate(hostname)`
- `check_http_status(url)`
- `check_dns_resolution(hostname)`

## Start The Server

```bash
python -m mcp_server.server
```

By default the server listens on `http://localhost:8081/mcp`.

You can override the bind settings with:

- `MCP_SERVER_HOST`
- `MCP_SERVER_PORT`
- `MCP_STREAMABLE_HTTP_PATH`

Example:

```bash
MCP_SERVER_PORT=8000 python -m mcp_server.server
```

## Test The MCP Path

Start the server in one terminal, then run:

```bash
python main.py https://google.com https://expired.badssl.com --mcp
```

If the MCP path is working, the pipeline will print:

```text
[MCP] Using MCP server for health checks
```

and the discovery phase will use MCP-backed health tools instead of direct Python function calls.

## Hosted MCP Path

If you configure:

- `AZURE_AI_PROJECT_ENDPOINT`
- `AZURE_AI_MODEL_DEPLOYMENT_NAME`
- `MCP_SERVER_URL=https://your-public-mcp-endpoint/mcp`

then the Discovery agent uses the hosted MCP tool path so Azure executes the MCP calls remotely.
