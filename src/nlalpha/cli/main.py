"""Console entry point for the NLAlpha bundle."""

import argparse

from .doctor import run_doctor
from .runtime import DEFAULT_PORTS
from .serve import run_serve
from .up import run_down, run_mcp_config, run_status, run_up


def _add_state_dir(parser) -> None:
    """Add the shared state directory option."""
    parser.add_argument("--state-dir", default="~/.nlalpha", help="Runtime state directory")


def main(argv=None) -> int:
    """Parse one bundle command and dispatch it."""
    parser = argparse.ArgumentParser(prog="nlalpha", description="NLAlpha bundle utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="Inspect installed packages and plugin entry points")
    doctor.set_defaults(handler=run_doctor)
    serve = subparsers.add_parser("serve", help="Run one NLAlpha MCP service")
    serve.add_argument("service", choices=("data", "strategy", "capability", "backtest"))
    serve.set_defaults(handler=run_serve)
    up = subparsers.add_parser("up", help="Start the four MCP services and a disposable Redis")
    up.add_argument("--provider", choices=("yfinance", "tushare"), default="yfinance")
    up.add_argument("--redis-url", help="Use an existing Redis instead of starting one")
    for name, default in DEFAULT_PORTS.items():
        up.add_argument(f"--{name}-port", type=int, default=default)
    _add_state_dir(up)
    up.set_defaults(handler=run_up)
    down = subparsers.add_parser("down", help="Stop local services")
    _add_state_dir(down)
    down.set_defaults(handler=run_down)
    status = subparsers.add_parser("status", help="Show local service status")
    _add_state_dir(status)
    status.set_defaults(handler=run_status)
    mcp_config = subparsers.add_parser("mcp-config", help="Print MCP client configuration")
    _add_state_dir(mcp_config)
    mcp_config.set_defaults(handler=run_mcp_config)
    args = parser.parse_args(argv)
    return args.handler(args)
