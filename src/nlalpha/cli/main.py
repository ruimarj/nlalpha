"""Console entry point for the NLAlpha bundle."""

import argparse

from .doctor import run_doctor
from .serve import run_serve


def main(argv=None) -> int:
    """Parse one bundle command and dispatch it."""
    parser = argparse.ArgumentParser(prog="nlalpha", description="NLAlpha bundle utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="Inspect installed packages and plugin entry points")
    doctor.set_defaults(handler=run_doctor)
    serve = subparsers.add_parser("serve", help="Run one NLAlpha MCP service")
    serve.add_argument("service", choices=("data", "strategy", "capability", "backtest"))
    serve.set_defaults(handler=run_serve)
    args = parser.parse_args(argv)
    return args.handler(args)
