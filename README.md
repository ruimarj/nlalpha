# nlalpha

Install-and-use bundle for the NLAlpha community backtesting stack. It pins ten
distributions (the community set with `yfinance` in place of the optional Tushare
provider) and provides a thin `nlalpha` command; it contains no domain logic of its own.

## Install

```bash
uv pip install nlalpha
```

The default installation pins `nlalpha-core`, `nlalpha-data`, `nlalpha-strategy`,
`nlalpha-backtest`, `nlalpha-capability`, `nlalpha-family-cta`, `nlalpha-nautilus`,
`nlalpha-talib`, `nlalpha-performance`, and `nlalpha-yfinance`. Use the package index
configured for your environment.

Tushare is available as an optional China-market provider:

```bash
uv pip install "nlalpha[china]"
```

Tushare requires `TUSHARE_TOKEN`; installing the extra does not grant data access.

The bundle pins all ten distributions exactly; every pinned version must be available
on the configured index.

## Commands

```text
nlalpha doctor
nlalpha serve data|strategy|capability|backtest
nlalpha up [options]
nlalpha down
nlalpha status
nlalpha mcp-config
```

`doctor` reports installed distribution versions and the discovered `nlalpha.engines`,
`nlalpha.strategies`, `nlalpha.capabilities`, `nlalpha.data`, and
`nlalpha.capability_server` entry points. `yfinance` is required; `tushare` is optional.

`serve` imports the selected service's `main` and runs it in the current process; the
services read `NLALPHA_HOST` and `NLALPHA_PORT`.

`up` starts the four MCP services in separate processes and a disposable Redis. It
writes runtime state under `~/.nlalpha` (`run.json`, logs, workspace, and the backtest
SQLite job store) and waits for `data`/`backtest` `/ready` and
`strategy`/`capability` `/health` before reporting success.

| Option | Default | Purpose |
|---|---|---|
| `--provider` | `yfinance` | Data provider; `tushare` requires the `china` extra and `TUSHARE_TOKEN`. |
| `--redis-url` | disposable Redis | Use an existing Redis instead of starting one. |
| `--data-port` | `8001` | Data service port. |
| `--strategy-port` | `8002` | Strategy service port. |
| `--capability-port` | `8003` | Capability service port. |
| `--backtest-port` | `8004` | Backtest service port. |
| `--state-dir` | `~/.nlalpha` | Runtime state directory. |

`down` stops the processes recorded in `run.json`, removes an owned Redis container or
process, and deletes the state file. `status` prints each service's port, process id,
and health plus Redis reachability. `mcp-config` prints JSON MCP client configuration
using `run.json` when present, otherwise the default ports.

## Extras

| Extra | Contents |
|---|---|
| `china` | `nlalpha-tushare` |
| `s3` | `nlalpha-data[s3]` and `nlalpha-backtest[redis]` |

Private Vector/statistics packages are not part of the community bundle; install them
from the private index explicitly.

## Requirements and limits

- `yfinance` is the default quick-start provider. It is unofficial and may be rate
  limited by the upstream service.
- Tushare is optional and requires both the `china` extra and `TUSHARE_TOKEN`.
- `up` starts Redis through Docker when available, then through `redis-server` on a
  loopback port. If neither is installed, pass `--redis-url` pointing at an existing
  Redis.
- The local stack binds services to `127.0.0.1` with single-user identity. It is a
  development and quick-start surface, not a hardened multi-user deployment.
- The platform adapter is not included; it carries platform identity, sandbox, and
  deployment semantics.
- Domain contracts and logic live in `nlalpha-core` and the service packages. The
  `nlalpha` distribution only contributes the `nlalpha.cli` namespace and dependency pins.

## Windows

Native Windows is supported with Python 3.12 and either Docker Desktop or an existing
Redis reachable through `--redis-url`. Run the commands from PowerShell; the default
state directory expands to `%USERPROFILE%\.nlalpha` (`~/.nlalpha` also works). Activate a
virtual environment with `.venv\Scripts\Activate.ps1`. `redis-server` is usually not
installed on Windows, so Docker Desktop is the recommended local Redis. `down` stops
each service process tree with `taskkill /T /F`.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install pytest
PYTHONPATH=src pytest tests -q
pip install -e . --no-deps
nlalpha doctor
```

`doctor` reports any missing required distributions and missing plugin entry-point
groups; it exits nonzero until every pinned package is installed.
