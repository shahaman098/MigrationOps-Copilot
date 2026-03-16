#!/bin/bash
set -e

pip install -r requirements.txt --pre
export MCP_SERVER_HOST="0.0.0.0"
export MCP_SERVER_PORT="${PORT:-8000}"
export MCP_STREAMABLE_HTTP_PATH="${MCP_STREAMABLE_HTTP_PATH:-/mcp}"
python -m mcp_server.server
