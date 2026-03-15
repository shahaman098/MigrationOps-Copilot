"""What is REAL: SSL, HTTP, and DNS checks against live endpoints.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import json
import socket
import ssl
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
from agent_framework import tool


def _extract_name(entries: tuple[tuple[tuple[str, str], ...], ...], field_name: str) -> str | None:
    for group in entries:
        for name, value in group:
            if name == field_name:
                return value
    return None


def _decode_peer_certificate(hostname: str) -> dict[str, object]:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.create_connection((hostname, 443), timeout=5) as raw_socket:
        with context.wrap_socket(raw_socket, server_hostname=hostname) as tls_socket:
            certificate_der = tls_socket.getpeercert(binary_form=True)

    certificate_pem = ssl.DER_cert_to_PEM_cert(certificate_der)

    with tempfile.NamedTemporaryFile("w", delete=False) as certificate_file:
        certificate_file.write(certificate_pem)
        certificate_path = Path(certificate_file.name)

    try:
        return ssl._ssl._test_decode_cert(str(certificate_path))
    finally:
        certificate_path.unlink(missing_ok=True)


@tool(
    name="check_ssl_certificate",
    description="Perform a real TLS handshake and inspect the remote certificate for expiry details.",
)
def check_ssl_certificate(
    hostname: Annotated[str, "The hostname to inspect on TCP port 443."],
) -> str:
    try:
        started_at = time.perf_counter()
        certificate = _decode_peer_certificate(hostname)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

        subject = certificate.get("subject", ())
        issuer_entries = certificate.get("issuer", ())
        not_after_raw = certificate["notAfter"]

        common_name = _extract_name(subject, "commonName")
        issuer = _extract_name(issuer_entries, "commonName") or _extract_name(
            issuer_entries,
            "organizationName",
        )

        expires_at = datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=UTC,
        )
        now = datetime.now(UTC)
        days_until_expiry = int((expires_at - now).total_seconds() // 86400)
        is_expired = expires_at <= now
        is_expiring_soon = not is_expired and days_until_expiry <= 30

        return json.dumps(
            {
                "status": "ok",
                "hostname": hostname,
                "days_until_expiry": days_until_expiry,
                "is_expired": is_expired,
                "is_expiring_soon": is_expiring_soon,
                "issuer": issuer,
                "common_name": common_name,
                "checked_in_ms": elapsed_ms,
            },
        )
    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "hostname": hostname,
                "error": str(exc),
            },
        )


@tool(
    name="check_http_status",
    description="Perform a real HTTP GET request and report status, latency, and redirect behavior.",
)
def check_http_status(
    url: Annotated[str, "The full URL to request over HTTP or HTTPS."],
) -> str:
    try:
        started_at = time.perf_counter()
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(url)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

        return json.dumps(
            {
                "status": "ok",
                "url": str(response.url),
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "was_redirected": len(response.history) > 0,
            },
        )
    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "url": url,
                "error": str(exc),
            },
        )


@tool(
    name="check_dns_resolution",
    description="Perform a real DNS lookup for a hostname and report the resolved IP addresses.",
)
def check_dns_resolution(
    hostname: Annotated[str, "The hostname to resolve via DNS."],
) -> str:
    try:
        started_at = time.perf_counter()
        address_info = socket.getaddrinfo(hostname, None)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        resolved_ips = sorted({result[4][0] for result in address_info})

        return json.dumps(
            {
                "status": "ok",
                "hostname": hostname,
                "resolved_ips": resolved_ips,
                "ip_count": len(resolved_ips),
                "resolution_time_ms": elapsed_ms,
            },
        )
    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "hostname": hostname,
                "error": str(exc),
            },
        )
