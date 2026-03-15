"""What is REAL: All comparisons use real snapshot data.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import json
from datetime import UTC, datetime
from urllib.parse import urlparse

from tools.health_checks import (
    check_dns_resolution,
    check_http_status,
    check_ssl_certificate,
)

# VERIFY: "Significant" SSL expiry drop is defined as a decrease of more than 30 days.
SIGNIFICANT_EXPIRY_DROP_DAYS = 30

# VERIFY: To avoid transient latency noise, the >2x response-time rule also requires
# an absolute increase of more than 500 ms before flagging a warning.
RESPONSE_TIME_WARNING_ABSOLUTE_MS = 500.0


def _extract_hostname(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or url


def _http_is_2xx(status_code: object) -> bool:
    return isinstance(status_code, int) and 200 <= status_code < 300


def _add_change(
    changes: list[dict[str, object]],
    category: str,
    field: str,
    before: object,
    after: object,
    severity: str,
    description: str,
) -> None:
    changes.append(
        {
            "category": category,
            "field": field,
            "before": before,
            "after": after,
            "severity": severity,
            "description": description,
        },
    )


def _compare_ssl_fields(
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    changes: list[dict[str, object]],
) -> None:
    before_ssl = before_snapshot["ssl"]
    after_ssl = after_snapshot["ssl"]

    if before_ssl.get("status") != after_ssl.get("status"):
        severity = "critical" if after_ssl.get("status") == "error" else "high"
        _add_change(
            changes,
            "ssl",
            "status",
            before_ssl.get("status"),
            after_ssl.get("status"),
            severity,
            "SSL status changed",
        )

    if before_ssl.get("is_expired") != after_ssl.get("is_expired"):
        severity = "critical" if after_ssl.get("is_expired") is True else "high"
        _add_change(
            changes,
            "ssl",
            "is_expired",
            before_ssl.get("is_expired"),
            after_ssl.get("is_expired"),
            severity,
            "SSL certificate expiry state changed",
        )

    if before_ssl.get("is_expiring_soon") != after_ssl.get("is_expiring_soon"):
        _add_change(
            changes,
            "ssl",
            "is_expiring_soon",
            before_ssl.get("is_expiring_soon"),
            after_ssl.get("is_expiring_soon"),
            "warning",
            "SSL certificate expiring-soon state changed",
        )

    if before_ssl.get("issuer") != after_ssl.get("issuer"):
        _add_change(
            changes,
            "ssl",
            "issuer",
            before_ssl.get("issuer"),
            after_ssl.get("issuer"),
            "high",
            "SSL certificate issuer changed",
        )

    if before_ssl.get("common_name") != after_ssl.get("common_name"):
        _add_change(
            changes,
            "ssl",
            "common_name",
            before_ssl.get("common_name"),
            after_ssl.get("common_name"),
            "high",
            "SSL certificate common name changed",
        )

    before_days = before_ssl.get("days_until_expiry")
    after_days = after_ssl.get("days_until_expiry")
    if isinstance(before_days, int) and isinstance(after_days, int):
        if before_days - after_days > SIGNIFICANT_EXPIRY_DROP_DAYS:
            _add_change(
                changes,
                "ssl",
                "days_until_expiry",
                before_days,
                after_days,
                "warning",
                "SSL certificate days until expiry dropped significantly",
            )

    if after_ssl.get("status") == "error":
        _add_change(
            changes,
            "ssl",
            "status",
            before_ssl.get("status"),
            after_ssl.get("status"),
            "critical",
            "SSL check failed on the target snapshot",
        )

    if after_ssl.get("is_expired") is True:
        _add_change(
            changes,
            "ssl",
            "is_expired",
            before_ssl.get("is_expired"),
            after_ssl.get("is_expired"),
            "critical",
            "Target SSL certificate is expired",
        )


def _compare_http_fields(
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    changes: list[dict[str, object]],
) -> None:
    before_http = before_snapshot["http"]
    after_http = after_snapshot["http"]

    if before_http.get("status") != after_http.get("status"):
        severity = "critical" if after_http.get("status") == "error" else "high"
        _add_change(
            changes,
            "http",
            "status",
            before_http.get("status"),
            after_http.get("status"),
            severity,
            "HTTP check status changed",
        )

    before_status_code = before_http.get("status_code")
    after_status_code = after_http.get("status_code")
    if before_status_code != after_status_code:
        severity = "info"
        if _http_is_2xx(before_status_code) and (
            isinstance(after_status_code, int) and 400 <= after_status_code < 600
        ):
            severity = "critical"
        _add_change(
            changes,
            "http",
            "status_code",
            before_status_code,
            after_status_code,
            severity,
            "HTTP status code changed",
        )

    before_response_time = before_http.get("response_time_ms")
    after_response_time = after_http.get("response_time_ms")
    if isinstance(before_response_time, (int, float)) and isinstance(after_response_time, (int, float)):
        if (
            before_response_time > 0
            and after_response_time > before_response_time * 2
            and (after_response_time - before_response_time) > RESPONSE_TIME_WARNING_ABSOLUTE_MS
        ):
            _add_change(
                changes,
                "http",
                "response_time_ms",
                before_response_time,
                after_response_time,
                "warning",
                "HTTP response time increased by more than 2x",
            )

    if after_http.get("status") == "error":
        _add_change(
            changes,
            "http",
            "status",
            before_http.get("status"),
            after_http.get("status"),
            "critical",
            "HTTP check failed on the target snapshot",
        )


def _compare_dns_fields(
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    changes: list[dict[str, object]],
) -> None:
    before_dns = before_snapshot["dns"]
    after_dns = after_snapshot["dns"]

    if before_dns.get("status") != after_dns.get("status"):
        severity = "critical" if after_dns.get("status") == "error" else "info"
        _add_change(
            changes,
            "dns",
            "status",
            before_dns.get("status"),
            after_dns.get("status"),
            severity,
            "DNS resolution status changed",
        )

    before_ips = sorted(before_dns.get("resolved_ips", []))
    after_ips = sorted(after_dns.get("resolved_ips", []))
    if before_ips != after_ips:
        _add_change(
            changes,
            "dns",
            "resolved_ips",
            before_ips,
            after_ips,
            "info",
            "DNS resolved IPs changed",
        )

    if after_dns.get("status") == "error":
        _add_change(
            changes,
            "dns",
            "status",
            before_dns.get("status"),
            after_dns.get("status"),
            "critical",
            "DNS resolution failed on the target snapshot",
        )


def _calculate_summary(changes: list[dict[str, object]]) -> dict[str, int]:
    critical_changes = sum(1 for change in changes if change["severity"] == "critical")
    warning_changes = sum(1 for change in changes if change["severity"] == "warning")
    info_changes = sum(1 for change in changes if change["severity"] == "info")

    return {
        "total_changes": len(changes),
        "critical_changes": critical_changes,
        "warning_changes": warning_changes,
        "info_changes": info_changes,
    }


def _overall_risk(changes: list[dict[str, object]]) -> str:
    severities = {str(change["severity"]).lower() for change in changes}
    if "critical" in severities:
        return "CRITICAL"
    if "high" in severities:
        return "HIGH"
    if "warning" in severities:
        return "MEDIUM"
    if "info" in severities:
        return "LOW"
    return "LOW"


async def snapshot_site(url: str) -> str:
    hostname = _extract_hostname(url)
    ssl_result = json.loads(check_ssl_certificate(hostname))
    http_result = json.loads(check_http_status(url))
    dns_result = json.loads(check_dns_resolution(hostname))

    snapshot = {
        "url": url,
        "hostname": hostname,
        "timestamp": datetime.now(UTC).isoformat(),
        "ssl": ssl_result,
        "http": http_result,
        "dns": dns_result,
    }
    return json.dumps(snapshot)


def compare_snapshots(before: str, after: str) -> str:
    before_snapshot = json.loads(before)
    after_snapshot = json.loads(after)
    changes: list[dict[str, object]] = []

    _compare_ssl_fields(before_snapshot, after_snapshot, changes)
    _compare_http_fields(before_snapshot, after_snapshot, changes)
    _compare_dns_fields(before_snapshot, after_snapshot, changes)

    comparison = {
        "source_url": before_snapshot["url"],
        "target_url": after_snapshot["url"],
        "changes": changes,
        "summary": _calculate_summary(changes),
        "overall_risk": _overall_risk(changes),
    }
    return json.dumps(comparison)
