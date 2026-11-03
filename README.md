# nlalpha

Install-and-use bundle for the NLAlpha community backtesting stack. It depends on the
ten community distributions and provides a thin `nlalpha` command; it contains no domain
logic of its own.

## Install

```bash
uv pip install nlalpha
```

Use the package index configured for your environment (for example `UV_INDEX_URL`, or
`pip --index-url`). Internal deployments inject their index through the deployment
environment; no index address is committed here.

The bundle pins all ten community distributions exactly; every pinned version must be
available on the configured index.

## Commands

```text
nlalpha doctor
nlalpha serve data|strategy|capability|backtest
```

`doctor` reports installed distribution versions and the discovered `nlalpha.engines`,
`nlalpha.strategies`, `nlalpha.capabilities`, `nlalpha.data`, and
`nlalpha.capability_server` entry points. `serve` imports the selected service's `main`
and runs it in the current process; the services read `NLALPHA_HOST` and `NLALPHA_PORT`.

## Extras

| Extra | Contents |
|---|---|
| `s3` | `nlalpha-data[s3]` and `nlalpha-backtest[redis]` |

Private Vector/statistics packages are not part of the community bundle; install them
from the private index explicitly.

## Boundaries

- Tushare requires `TUSHARE_TOKEN`; installing the bundle does not grant data access.
- The platform adapter is not included; it carries platform identity, sandbox, and deployment semantics.
- Domain contracts and logic live in `nlalpha-core` and the service packages. The
  `nlalpha` distribution only contributes the `nlalpha.cli` namespace and dependency pins.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install pytest
PYTHONPATH=src pytest tests -q
pip install -e . --no-deps
nlalpha doctor
```

`doctor` reports any missing distributions and missing plugin entry-point groups; it
exits nonzero until every pinned package is installed.
