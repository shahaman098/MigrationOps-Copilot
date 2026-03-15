"""What is REAL: Tool exports for real health checks and baseline comparisons.
What is MOCKED: Nothing.
What is SIMULATED: Remediation tool exports.
"""

from tools.baseline import compare_snapshots, snapshot_site
from tools.health_checks import (
    check_dns_resolution,
    check_http_status,
    check_ssl_certificate,
)
from tools.remediation import (
    simulate_cache_purge,
    simulate_cert_renewal,
    simulate_config_update,
)

__all__ = [
    "snapshot_site",
    "compare_snapshots",
    "check_dns_resolution",
    "check_http_status",
    "check_ssl_certificate",
    "simulate_cert_renewal",
    "simulate_cache_purge",
    "simulate_config_update",
]
