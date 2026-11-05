# nlalpha

NLAlpha community backtesting stack as one install-and-run bundle. It pins ten
distributions and provides the `nlalpha` command for the four MCP services: data,
strategy, capability, and backtest.

## Quick start (Docker Compose)

Prerequisite: Docker Engine or Docker Desktop with the Compose plugin.

```bash
git clone https://github.com/ruimarj/nlalpha.git
cd nlalpha
docker compose up -d
```

The stack runs Redis and the four MCP services in containers. Every host port binds to
loopback:

| Service | URL | Health |
|---|---|---|
| data | `http://127.0.0.1:8001` | `/ready` |
| strategy | `http://127.0.0.1:8002` | `/health` |
| capability | `http://127.0.0.1:8003` | `/health` |
| backtest | `http://127.0.0.1:8004` | `/ready` |

MCP clients connect to the `/mcp` endpoint of each service:

```json
{
  "mcpServers": {
    "nlalpha-data": {"url": "http://127.0.0.1:8001/mcp"},
    "nlalpha-strategy": {"url": "http://127.0.0.1:8002/mcp"},
    "nlalpha-capability": {"url": "http://127.0.0.1:8003/mcp"},
    "nlalpha-backtest": {"url": "http://127.0.0.1:8004/mcp"}
  }
}
```

Inspect the stack with `docker compose ps` and stop it with:

```bash
docker compose down
```

`docker compose down -v` also removes the `nlalpha-state` volume, which contains the
workspace and the backtest job store.

### Configuration

The default image is `ghcr.io/ruimarj/nlalpha:0.2.3`. Set these variables before
`docker compose up -d` to change the image, ports, or data provider:

| Variable | Default | Purpose |
|---|---|---|
| `NLALPHA_IMAGE` | `ghcr.io/ruimarj/nlalpha:0.2.3` | Container image. |
| `NLALPHA_DATA_PORT` | `8001` | Host port for the data service. |
| `NLALPHA_STRATEGY_PORT` | `8002` | Host port for the strategy service. |
| `NLALPHA_CAPABILITY_PORT` | `8003` | Host port for the capability service. |
| `NLALPHA_BACKTEST_PORT` | `8004` | Host port for the backtest service. |
| `NLALPHA_DATA_PROVIDER` | `yfinance` | Market data provider. |
| `TUSHARE_TOKEN` | empty | Token used when the provider is `tushare`. |

```bash
NLALPHA_DATA_PORT=18001 NLALPHA_STRATEGY_PORT=18002 \
NLALPHA_CAPABILITY_PORT=18003 NLALPHA_BACKTEST_PORT=18004 \
docker compose up -d
```

`yfinance` is the default provider and needs no credentials. The published image also
ships Tushare; select it with `NLALPHA_DATA_PROVIDER=tushare` and a `TUSHARE_TOKEN`
that has the required data permissions:

```bash
export TUSHARE_TOKEN=...
export NLALPHA_DATA_PROVIDER=tushare
docker compose up -d
```

Python installs use the `china` extra to add Tushare.

## Local Python mode

Use local Python mode for development or when the services should run as host processes.

Prerequisite: Python 3.12 and Redis. Redis can come from Docker, a local
`redis-server`, or an existing server passed through `--redis-url`.

```bash
pip install nlalpha
nlalpha doctor
nlalpha up
nlalpha status
nlalpha mcp-config
nlalpha down
```

`nlalpha up` starts Redis and the four services, writes runtime state under
`~/.nlalpha`, and waits for the same health endpoints before reporting success. The
services bind to `127.0.0.1`. `nlalpha down` stops the processes and removes the Redis
instance it started. `nlalpha mcp-config` prints the same MCP client configuration
shown above.

### Commands

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
`nlalpha.capability_server` entry points.

`serve` runs one service in the current process using `NLALPHA_HOST` and
`NLALPHA_PORT`.

`up` accepts:

| Option | Default | Purpose |
|---|---|---|
| `--provider` | `yfinance` | Data provider; `tushare` requires `TUSHARE_TOKEN` (included in the published image; Python installs use the `china` extra). |
| `--redis-url` | disposable Redis | Use an existing Redis instead of starting one. |
| `--docker` | off | Run the stack with Docker Compose. |
| `--image` | `ghcr.io/ruimarj/nlalpha:0.2.3` | Image used with `--docker`. |
| `--data-port` | `8001` | Data service port. |
| `--strategy-port` | `8002` | Strategy service port. |
| `--capability-port` | `8003` | Capability service port. |
| `--backtest-port` | `8004` | Backtest service port. |
| `--state-dir` | `~/.nlalpha` | Runtime state directory. |

`nlalpha up --docker` writes a Compose file under the state directory, starts the stack,
and waits for the host health endpoints. `nlalpha down` stops either mode.

## Package set

The bundle installs `nlalpha-core`, `nlalpha-data`, `nlalpha-strategy`,
`nlalpha-backtest`, `nlalpha-capability`, `nlalpha-family-cta`, `nlalpha-nautilus`,
`nlalpha-talib`, `nlalpha-performance`, and `nlalpha-yfinance`.

| Extra | Contents |
|---|---|
| `china` | `nlalpha-tushare` |
| `s3` | `nlalpha-data[s3]` and `nlalpha-backtest[redis]` |

```bash
pip install "nlalpha[china]"
```

Private Vector/statistics packages are not part of the community bundle.

## Windows

Docker Desktop is the recommended way to run the stack on Windows; the Quick start
commands work from PowerShell. Local Python mode needs Python 3.12 and a Redis instance,
usually provided by Docker Desktop. The default state directory expands to
`%USERPROFILE%\.nlalpha` (`~/.nlalpha` also works). Activate a virtual environment with
`.venv\Scripts\Activate.ps1`. `nlalpha down` stops each service process tree with
`taskkill /T /F`.

## Requirements and limits

- `yfinance` is the default provider. It is unofficial and may be rate limited by the
  upstream service.
- Tushare is included in the published image and requires `TUSHARE_TOKEN` with the
  necessary data permissions; Python installs use the `china` extra.
- The local stack binds services to `127.0.0.1` with single-user identity. It is a
  development and quick-start surface, not a hardened multi-user deployment.
- The platform adapter is not included; it carries platform identity, sandbox, and
  deployment semantics.
- Domain contracts and logic live in `nlalpha-core` and the service packages. The
  `nlalpha` distribution only contributes the `nlalpha.cli` namespace and dependency
  pins.
