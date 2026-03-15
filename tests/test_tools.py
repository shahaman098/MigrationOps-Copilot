"""What is REAL: Live SSL, HTTP, and DNS checks against public endpoints.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.health_checks import (
    check_dns_resolution,
    check_http_status,
    check_ssl_certificate,
)


def test_ssl_healthy() -> None:
    result = json.loads(check_ssl_certificate("google.com"))
    assert result["status"] == "ok", result
    assert result["hostname"] == "google.com", result
    assert result["is_expired"] is False, result
    assert isinstance(result["days_until_expiry"], int), result
    assert result["common_name"], result


def test_ssl_expired() -> None:
    result = json.loads(check_ssl_certificate("expired.badssl.com"))
    assert result["status"] == "ok", result
    assert result["hostname"] == "expired.badssl.com", result
    assert result["is_expired"] is True, result
    assert result["days_until_expiry"] < 0, result


def test_http_status() -> None:
    result = json.loads(check_http_status("https://httpbin.org/status/200"))
    assert result["status"] == "ok", result
    assert result["status_code"] == 200, result
    assert result["response_time_ms"] >= 0, result


def test_dns_resolution_success() -> None:
    result = json.loads(check_dns_resolution("google.com"))
    assert result["status"] == "ok", result
    assert result["hostname"] == "google.com", result
    assert result["ip_count"] > 0, result
    assert len(result["resolved_ips"]) == result["ip_count"], result


def test_dns_resolution_failure() -> None:
    result = json.loads(check_dns_resolution("nonexistent-siteops-guardian.invalid"))
    assert result["status"] == "error", result
    assert result["hostname"] == "nonexistent-siteops-guardian.invalid", result
    assert result["error"], result


def main() -> None:
    test_ssl_healthy()
    test_ssl_expired()
    test_http_status()
    test_dns_resolution_success()
    test_dns_resolution_failure()
    print("All Phase 1 tool tests passed.")


if __name__ == "__main__":
    main()
