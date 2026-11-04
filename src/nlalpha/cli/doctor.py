"""Report installed NLAlpha distributions and plugin entry points."""

from importlib.metadata import PackageNotFoundError, entry_points, version
import os

REQUIRED_DISTRIBUTIONS = (
    "nlalpha-core", "nlalpha-data", "nlalpha-strategy", "nlalpha-backtest",
    "nlalpha-capability", "nlalpha-family-cta", "nlalpha-nautilus",
    "nlalpha-talib", "nlalpha-performance", "nlalpha-yfinance",
)
OPTIONAL_DISTRIBUTIONS = ("nlalpha-tushare",)
ENTRY_POINT_GROUPS = (
    "nlalpha.engines", "nlalpha.strategies", "nlalpha.capabilities",
    "nlalpha.data", "nlalpha.capability_server",
)
REQUIRED_DATA_PROVIDERS = ("yfinance",)


def distribution_installed(name: str) -> bool:
    """Return whether a distribution is installed."""
    try:
        version(name)
    except PackageNotFoundError:
        return False
    return True


def run_doctor(_args) -> int:
    """Print bundle status and return nonzero when a required part is missing."""
    exit_code = 0
    print("NLAlpha bundle")
    for name in REQUIRED_DISTRIBUTIONS:
        try:
            print(f"  {name} {version(name)}")
        except PackageNotFoundError:
            print(f"  {name} MISSING")
            exit_code = 1
    for name in OPTIONAL_DISTRIBUTIONS:
        try:
            print(f"  {name} {version(name)}")
        except PackageNotFoundError:
            print(f"  {name} not installed (optional)")
    entry_names = {}
    for group in ENTRY_POINT_GROUPS:
        names = sorted(entry.name for entry in entry_points(group=group))
        entry_names[group] = names
        print(f"{group}: {', '.join(names) if names else '(none)'}")
        if not names:
            exit_code = 1
    data_providers = entry_names["nlalpha.data"]
    missing = [name for name in REQUIRED_DATA_PROVIDERS if name not in data_providers]
    if missing:
        print(f"nlalpha.data: missing required provider(s): {', '.join(missing)}")
        exit_code = 1
    if "tushare" in data_providers or distribution_installed("nlalpha-tushare"):
        if not os.environ.get("TUSHARE_TOKEN"):
            print("TUSHARE_TOKEN: not set (set it and NLALPHA_DATA_PROVIDER=tushare to use Tushare)")
    print("Next: `nlalpha up` starts the four local services; `nlalpha serve ...` runs one service")
    return exit_code
