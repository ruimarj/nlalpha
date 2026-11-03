"""Run one installed NLAlpha MCP service in the current process."""

from importlib import import_module

SERVICES = {
    "data": "nlalpha_data.server",
    "strategy": "nlalpha_strategy.server",
    "capability": "nlalpha_capability.server",
    "backtest": "nlalpha_backtest.server",
}


def run_serve(args) -> int:
    """Import and run the selected service's main function."""
    module = import_module(SERVICES[args.service])
    module.main()
    return 0
