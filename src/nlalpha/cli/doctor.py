"""Report installed NLAlpha distributions and plugin entry points."""

from importlib.metadata import PackageNotFoundError, entry_points, version
import os

DISTRIBUTIONS = (
    "nlalpha-core", "nlalpha-data", "nlalpha-strategy", "nlalpha-backtest",
    "nlalpha-capability", "nlalpha-family-cta", "nlalpha-nautilus",
    "nlalpha-tushare", "nlalpha-talib", "nlalpha-performance",
)
ENTRY_POINT_GROUPS = (
    "nlalpha.engines", "nlalpha.strategies", "nlalpha.capabilities",
    "nlalpha.data", "nlalpha.capability_server",
)


def run_doctor(_args) -> int:
    """Print bundle status and return nonzero when a required part is missing."""
    exit_code = 0
    print("NLAlpha bundle")
    for name in DISTRIBUTIONS:
        try:
            print(f"  {name} {version(name)}")
        except PackageNotFoundError:
            print(f"  {name} MISSING")
            exit_code = 1
    for group in ENTRY_POINT_GROUPS:
        names = sorted(entry.name for entry in entry_points(group=group))
        print(f"{group}: {', '.join(names) if names else '(none)'}")
        if not names:
            exit_code = 1
    if not os.environ.get("TUSHARE_TOKEN"):
        print("TUSHARE_TOKEN: not set (Tushare data source will be unavailable)")
    print("Next: `nlalpha serve data|strategy|capability|backtest` (NLALPHA_HOST / NLALPHA_PORT)")
    return exit_code
