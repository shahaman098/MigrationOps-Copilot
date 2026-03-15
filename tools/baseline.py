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

SIGNIFICANT_EXPIRY_DROP_DAYS = 30
RESPONSE_TIME_WARNING_MULTIPLIER = 2.0
RESPONSE_TIME_WARNING_ABSOLUTE_MS = 500.0
FINDING_ORDER = [
    "ssl_status_error",
    "ssl_expired",
    "ssl_expiring_soon",
    "ssl_issuer_changed",
    "ssl_common_name_changed",
    "ssl_days_until_expiry_dropped",
    "http_status_failed",
    "http_status_regressed_4xx",
    "http_status_regressed_5xx",
    "http_response_time_increased",
    "dns_resolution_failed",
    "dns_ips_changed",
]
HEALTH_SCORE_WEIGHTS = {
    "critical": 25,
    "high": 15,
    "warning": 5,
    "info": 0,
}


def _extract_hostname(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or url


def _http_is_2xx(status_code: object) -> bool:
    return isinstance(status_code, int) and 200 <= status_code < 300


def _record_change(
    changes_by_id: dict[str, dict[str, object]],
    finding_id: str,
    category: str,
    field: str,
    before: object,
    after: object,
    severity: str,
    description: str,
) -> None:
    if finding_id in changes_by_id:
        return

    changes_by_id[finding_id] = {
        "id": finding_id,
        "category": category,
        "field": field,
        "before": before,
        "after": after,
        "severity": severity,
        "description": description,
    }


def _compare_ssl_fields(
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    changes_by_id: dict[str, dict[str, object]],
) -> None:
    before_ssl = before_snapshot["ssl"]
    after_ssl = after_snapshot["ssl"]
    before_status = before_ssl.get("status")
    after_status = after_ssl.get("status")

    if after_status == "error" and before_status != "error":
        _record_change(
            changes_by_id,
            "ssl_status_error",
            "ssl",
            "status",
            before_status,
            after_status,
            "critical",
            "SSL certificate check failed on the target snapshot.",
        )
        return

    if after_ssl.get("is_expired") is True and before_ssl.get("is_expired") is not True:
        _record_change(
            changes_by_id,
            "ssl_expired",
            "ssl",
            "is_expired",
            before_ssl.get("is_expired"),
            after_ssl.get("is_expired"),
            "critical",
            "Target SSL certificate is expired.",
        )

    if after_ssl.get("is_expiring_soon") is True and before_ssl.get("is_expiring_soon") is not True:
        _record_change(
            changes_by_id,
            "ssl_expiring_soon",
            "ssl",
            "is_expiring_soon",
            before_ssl.get("is_expiring_soon"),
            after_ssl.get("is_expiring_soon"),
            "warning",
            "Target SSL certificate will expire within 30 days.",
        )

    if before_status == "ok" and after_status == "ok":
        if before_ssl.get("issuer") != after_ssl.get("issuer"):
            _record_change(
                changes_by_id,
                "ssl_issuer_changed",
                "ssl",
                "issuer",
                before_ssl.get("issuer"),
                after_ssl.get("issuer"),
                "high",
                "SSL certificate issuer changed.",
            )

        if before_ssl.get("common_name") != after_ssl.get("common_name"):
            _record_change(
                changes_by_id,
                "ssl_common_name_changed",
                "ssl",
                "common_name",
                before_ssl.get("common_name"),
                after_ssl.get("common_name"),
                "high",
                "SSL certificate common name changed.",
            )

        before_days = before_ssl.get("days_until_expiry")
        after_days = after_ssl.get("days_until_expiry")
        if (
            isinstance(before_days, int)
            and isinstance(after_days, int)
            and before_days - after_days > SIGNIFICANT_EXPIRY_DROP_DAYS
        ):
            _record_change(
                changes_by_id,
                "ssl_days_until_expiry_dropped",
                "ssl",
                "days_until_expiry",
                before_days,
                after_days,
                "warning",
                "SSL certificate days until expiry dropped significantly.",
            )


def _compare_http_fields(
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    changes_by_id: dict[str, dict[str, object]],
) -> None:
    before_http = before_snapshot["http"]
    after_http = after_snapshot["http"]
    before_status = before_http.get("status")
    after_status = after_http.get("status")
    before_status_code = before_http.get("status_code")
    after_status_code = after_http.get("status_code")

    if after_status == "error" and before_status != "error":
        _record_change(
            changes_by_id,
            "http_status_failed",
            "http",
            "status",
            before_status,
            after_status,
            "critical",
            "HTTP verification failed on the target snapshot.",
        )
        return

    if _http_is_2xx(before_status_code) and isinstance(after_status_code, int):
        if 500 <= after_status_code < 600:
            _record_change(
                changes_by_id,
                "http_status_regressed_5xx",
                "http",
                "status_code",
                before_status_code,
                after_status_code,
                "critical",
                "HTTP status regressed from healthy to a 5xx server error.",
            )
        elif 400 <= after_status_code < 500:
            _record_change(
                changes_by_id,
                "http_status_regressed_4xx",
                "http",
                "status_code",
                before_status_code,
                after_status_code,
                "high",
                "HTTP status regressed from healthy to a 4xx client error.",
            )

    before_response_time = before_http.get("response_time_ms")
    after_response_time = after_http.get("response_time_ms")
    if (
        before_status == "ok"
        and after_status == "ok"
        and isinstance(before_response_time, (int, float))
        and isinstance(after_response_time, (int, float))
        and before_response_time > 0
        and after_response_time > before_response_time * RESPONSE_TIME_WARNING_MULTIPLIER
        and (after_response_time - before_response_time) > RESPONSE_TIME_WARNING_ABSOLUTE_MS
    ):
        _record_change(
            changes_by_id,
            "http_response_time_increased",
            "http",
            "response_time_ms",
            before_response_time,
            after_response_time,
            "warning",
            "HTTP response time increased by more than 2x.",
        )


def _compare_dns_fields(
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    changes_by_id: dict[str, dict[str, object]],
) -> None:
    before_dns = before_snapshot["dns"]
    after_dns = after_snapshot["dns"]
    before_status = before_dns.get("status")
    after_status = after_dns.get("status")

    if after_status == "error" and before_status != "error":
        _record_change(
            changes_by_id,
            "dns_resolution_failed",
            "dns",
            "status",
            before_status,
            after_status,
            "critical",
            "DNS resolution failed on the target snapshot.",
        )
        return

    before_ips = sorted(before_dns.get("resolved_ips", []))
    after_ips = sorted(after_dns.get("resolved_ips", []))
    if before_status == "ok" and after_status == "ok" and before_ips != after_ips:
        _record_change(
            changes_by_id,
            "dns_ips_changed",
            "dns",
            "resolved_ips",
            before_ips,
            after_ips,
            "info",
            "DNS resolved IPs changed. This is expected during many migrations but should still be reviewed.",
        )


def _order_changes(changes_by_id: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    ordered_changes: list[dict[str, object]] = []
    for finding_id in FINDING_ORDER:
        change = changes_by_id.get(finding_id)
        if change is not None:
            ordered_changes.append(change)
    return ordered_changes


def _calculate_summary(changes: list[dict[str, object]]) -> dict[str, int]:
    critical_changes = sum(1 for change in changes if change["severity"] == "critical")
    high_changes = sum(1 for change in changes if change["severity"] == "high")
    warning_changes = sum(1 for change in changes if change["severity"] == "warning")
    info_changes = sum(1 for change in changes if change["severity"] == "info")
    migration_health_score = max(
        0,
        100
        - critical_changes * HEALTH_SCORE_WEIGHTS["critical"]
        - high_changes * HEALTH_SCORE_WEIGHTS["high"]
        - warning_changes * HEALTH_SCORE_WEIGHTS["warning"]
        - info_changes * HEALTH_SCORE_WEIGHTS["info"],
    )

    return {
        "total_changes": len(changes),
        "critical_changes": critical_changes,
        "high_changes": high_changes,
        "warning_changes": warning_changes,
        "info_changes": info_changes,
        "migration_health_score": migration_health_score,
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
    changes_by_id: dict[str, dict[str, object]] = {}

    _compare_ssl_fields(before_snapshot, after_snapshot, changes_by_id)
    _compare_http_fields(before_snapshot, after_snapshot, changes_by_id)
    _compare_dns_fields(before_snapshot, after_snapshot, changes_by_id)

    changes = _order_changes(changes_by_id)
    comparison = {
        "source_url": before_snapshot["url"],
        "target_url": after_snapshot["url"],
        "changes": changes,
        "summary": _calculate_summary(changes),
        "overall_risk": _overall_risk(changes),
    }
    return json.dumps(comparison)
