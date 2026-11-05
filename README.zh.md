# nlalpha

面向 NLAlpha 社区回测栈的安装即用包。它精确 pin 十个分发包，并提供 `nlalpha` 命令来运行四个 MCP 服务：data、strategy、capability 与 backtest。

## 快速开始（Docker Compose）

前置条件：Docker Engine，或带 Compose 插件的 Docker Desktop。

```bash
git clone https://github.com/ruimarj/nlalpha.git
cd nlalpha
docker compose up -d
```

该栈以容器运行 Redis 与四个 MCP 服务，所有宿主端口仅绑定回环地址：

| 服务 | URL | 健康检查 |
|---|---|---|
| data | `http://127.0.0.1:8001` | `/ready` |
| strategy | `http://127.0.0.1:8002` | `/health` |
| capability | `http://127.0.0.1:8003` | `/health` |
| backtest | `http://127.0.0.1:8004` | `/ready` |

MCP 客户端连接各服务的 `/mcp` 端点：

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

使用 `docker compose ps` 查看栈状态，使用以下命令停止：

```bash
docker compose down
```

`docker compose down -v` 还会删除 `nlalpha-state` 卷，其中包含工作区与回测任务库。

### 配置

默认镜像为 `ghcr.io/ruimarj/nlalpha:0.2.0`。在 `docker compose up -d` 前设置以下变量可更换镜像、端口或数据提供方：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `NLALPHA_IMAGE` | `ghcr.io/ruimarj/nlalpha:0.2.0` | 容器镜像。 |
| `NLALPHA_DATA_PORT` | `8001` | data 服务的宿主端口。 |
| `NLALPHA_STRATEGY_PORT` | `8002` | strategy 服务的宿主端口。 |
| `NLALPHA_CAPABILITY_PORT` | `8003` | capability 服务的宿主端口。 |
| `NLALPHA_BACKTEST_PORT` | `8004` | backtest 服务的宿主端口。 |
| `NLALPHA_DATA_PROVIDER` | `yfinance` | 行情数据提供方。 |
| `TUSHARE_TOKEN` | 空 | 提供方为 `tushare` 时使用的令牌。 |

```bash
NLALPHA_DATA_PORT=18001 NLALPHA_STRATEGY_PORT=18002 \
NLALPHA_CAPABILITY_PORT=18003 NLALPHA_BACKTEST_PORT=18004 \
docker compose up -d
```

`yfinance` 是默认提供方，无需凭据。发布镜像同时内置 Tushare；将 `NLALPHA_DATA_PROVIDER` 设为 `tushare`，并提供具备相应数据权限的 `TUSHARE_TOKEN` 即可：

```bash
export TUSHARE_TOKEN=...
export NLALPHA_DATA_PROVIDER=tushare
docker compose up -d
```

Python 安装用户通过 `china` 附加项获得 Tushare。

## 本地 Python 模式

在开发时，或需要将服务作为宿主机进程运行时，使用本地 Python 模式。

前置条件：Python 3.12 与 Redis。Redis 可来自 Docker、本地 `redis-server`，或通过 `--redis-url` 指向的已有服务。

```bash
pip install nlalpha
nlalpha doctor
nlalpha up
nlalpha status
nlalpha mcp-config
nlalpha down
```

`nlalpha up` 启动 Redis 与四个服务，将运行状态写入 `~/.nlalpha`，并在相同的健康端点就绪后才报告成功。服务绑定到 `127.0.0.1`。`nlalpha down` 停止这些进程并移除由本工具启动的 Redis。`nlalpha mcp-config` 输出与上文相同的 MCP 客户端配置。

### 命令

```text
nlalpha doctor
nlalpha serve data|strategy|capability|backtest
nlalpha up [选项]
nlalpha down
nlalpha status
nlalpha mcp-config
```

`doctor` 报告已安装分发版本以及发现的 `nlalpha.engines`、`nlalpha.strategies`、`nlalpha.capabilities`、`nlalpha.data` 与 `nlalpha.capability_server` 入口点。

`serve` 使用 `NLALPHA_HOST` 与 `NLALPHA_PORT` 在当前进程中运行一个服务。

`up` 接受：

| 选项 | 默认值 | 用途 |
|---|---|---|
| `--provider` | `yfinance` | 数据提供方；`tushare` 需要 `TUSHARE_TOKEN`（发布镜像已内置；Python 安装使用 `china` 附加项）。 |
| `--redis-url` | 一次性 Redis | 使用已有 Redis，而不是新启动一个。 |
| `--docker` | 关闭 | 使用 Docker Compose 运行栈。 |
| `--image` | `ghcr.io/ruimarj/nlalpha:0.2.0` | `--docker` 使用的镜像。 |
| `--data-port` | `8001` | data 服务端口。 |
| `--strategy-port` | `8002` | strategy 服务端口。 |
| `--capability-port` | `8003` | capability 服务端口。 |
| `--backtest-port` | `8004` | backtest 服务端口。 |
| `--state-dir` | `~/.nlalpha` | 运行状态目录。 |

`nlalpha up --docker` 在状态目录写入 Compose 文件，启动栈并等待宿主健康端点。`nlalpha down` 可停止两种模式。

## 包集合

本包安装 `nlalpha-core`、`nlalpha-data`、`nlalpha-strategy`、`nlalpha-backtest`、`nlalpha-capability`、`nlalpha-family-cta`、`nlalpha-nautilus`、`nlalpha-talib`、`nlalpha-performance` 与 `nlalpha-yfinance`。

| 附加项 | 内容 |
|---|---|
| `china` | `nlalpha-tushare` |
| `s3` | `nlalpha-data[s3]` 与 `nlalpha-backtest[redis]` |

```bash
pip install "nlalpha[china]"
```

私有 Vector/statistics 包不属于社区包。

## Windows

推荐使用 Docker Desktop 在 Windows 上运行栈；快速开始命令可在 PowerShell 中执行。本地 Python 模式需要 Python 3.12 与 Redis，通常由 Docker Desktop 提供。默认状态目录展开为 `%USERPROFILE%\.nlalpha`（`~/.nlalpha` 也可用）。虚拟环境使用 `.venv\Scripts\Activate.ps1` 激活。`nlalpha down` 使用 `taskkill /T /F` 停止各服务进程树。

## 要求与限制

- `yfinance` 是默认提供方。它属于非官方接入，可能受上游服务限流影响。
- 发布镜像已内置 Tushare，使用时需要具备相应数据权限的 `TUSHARE_TOKEN`；Python 安装通过 `china` 附加项获得。
- 本地栈将服务绑定到 `127.0.0.1` 并使用单用户身份，面向开发与快速开始，不是加固的多用户部署。
- 平台适配器不包含在内；它承载平台身份、沙箱与部署语义。
- 领域契约与逻辑位于 `nlalpha-core` 与各服务包中。`nlalpha` 分发仅提供 `nlalpha.cli` 命名空间与依赖版本锁定。
