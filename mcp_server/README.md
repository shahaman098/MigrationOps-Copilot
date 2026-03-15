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

The server listens on `http://localhost:8081/mcp`.

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
