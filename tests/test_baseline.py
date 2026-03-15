"""What is REAL: Snapshot and comparison tests against live public sites.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import json
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.baseline import compare_snapshots, snapshot_site


@pytest.mark.asyncio
async def test_snapshot_healthy_site() -> None:
    snapshot = json.loads(await snapshot_site("https://google.com"))
    assert snapshot["url"] == "https://google.com", snapshot
    assert snapshot["hostname"] == "google.com", snapshot
    assert snapshot["ssl"]["status"] == "ok", snapshot
    assert snapshot["http"]["status"] == "ok", snapshot
    assert snapshot["dns"]["status"] == "ok", snapshot


@pytest.mark.asyncio
async def test_snapshot_broken_site() -> None:
    snapshot = json.loads(await snapshot_site("https://expired.badssl.com"))
    assert snapshot["url"] == "https://expired.badssl.com", snapshot
    assert snapshot["hostname"] == "expired.badssl.com", snapshot
    assert snapshot["ssl"]["status"] in {"ok", "error"}, snapshot
    assert snapshot["ssl"].get("is_expired") is True or snapshot["ssl"]["status"] == "error", snapshot


@pytest.mark.asyncio
async def test_compare_identical() -> None:
    before = await snapshot_site("https://google.com")
    after = await snapshot_site("https://google.com")
    comparison = json.loads(compare_snapshots(before, after))

    assert comparison["source_url"] == "https://google.com", comparison
    assert comparison["target_url"] == "https://google.com", comparison
    assert comparison["overall_risk"] == "LOW", comparison
    assert comparison["summary"]["migration_health_score"] >= 95, comparison
    assert comparison["summary"]["total_changes"] == len(comparison["changes"]), comparison


@pytest.mark.asyncio
async def test_compare_broken_migration() -> None:
    before = await snapshot_site("https://google.com")
    after = await snapshot_site("https://expired.badssl.com")
    comparison = json.loads(compare_snapshots(before, after))
    finding_ids = {change["id"] for change in comparison["changes"]}

    assert comparison["overall_risk"] in {"CRITICAL", "HIGH"}, comparison
    assert comparison["summary"]["migration_health_score"] <= 50, comparison
    assert "ssl_expired" in finding_ids or "ssl_status_error" in finding_ids, comparison


@pytest.mark.asyncio
async def test_no_duplicate_findings() -> None:
    before = await snapshot_site("https://google.com")
    after = await snapshot_site("https://expired.badssl.com")
    comparison = json.loads(compare_snapshots(before, after))
    finding_ids = [change["id"] for change in comparison["changes"]]

    assert len(finding_ids) == len(set(finding_ids)), comparison

