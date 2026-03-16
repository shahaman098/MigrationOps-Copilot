"""What is REAL: MCP tool exposure for the live health-check functions.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import os

from mcp.server.fastmcp import FastMCP

from tools.health_checks import (
    check_dns_resolution as _check_dns_resolution,
    check_http_status as _check_http_status,
    check_ssl_certificate as _check_ssl_certificate,
)

MCP_SERVER_HOST = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = int(os.environ.get("MCP_SERVER_PORT", os.environ.get("PORT", "8081")))
MCP_STREAMABLE_HTTP_PATH = os.environ.get("MCP_STREAMABLE_HTTP_PATH", "/mcp")

mcp = FastMCP(
    "MigrationOps Health Checks",
    host=MCP_SERVER_HOST,
    port=MCP_SERVER_PORT,
    streamable_http_path=MCP_STREAMABLE_HTTP_PATH,
)


@mcp.tool(description="Check the SSL certificate for a hostname and return a JSON string.")
def check_ssl_certificate(hostname: str) -> str:
    return _check_ssl_certificate(hostname)


@mcp.tool(description="Check the HTTP status for a URL and return a JSON string.")
def check_http_status(url: str) -> str:
    return _check_http_status(url)


@mcp.tool(description="Resolve DNS for a hostname and return a JSON string.")
def check_dns_resolution(hostname: str) -> str:
    return _check_dns_resolution(hostname)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
