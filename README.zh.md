# nlalpha

面向 NLAlpha 社区回测栈的安装即用包。它精确 pin 十个分发包（社区包集合，以 `yfinance` 替代可选的 Tushare 提供方），并提供轻量的 `nlalpha` 命令；自身不包含领域逻辑。

## 安装

```bash
uv pip install nlalpha
```

默认安装包含 `nlalpha-core`、`nlalpha-data`、`nlalpha-strategy`、`nlalpha-backtest`、`nlalpha-capability`、`nlalpha-family-cta`、`nlalpha-nautilus`、`nlalpha-talib`、`nlalpha-performance` 与 `nlalpha-yfinance`。请使用为你的环境配置的包索引。

Tushare 是可选的 A 股数据提供方：

```bash
uv pip install "nlalpha[china]"
```

Tushare 需要 `TUSHARE_TOKEN`；安装附加项并不授予数据访问权限。

本包精确 pin 全部十个分发包；所有 pin 版本必须能在所配置的索引中解析。

## 命令

```text
nlalpha doctor
nlalpha serve data|strategy|capability|backtest
nlalpha up [选项]
nlalpha down
nlalpha status
nlalpha mcp-config
```

`doctor` 报告已安装分发版本以及发现的 `nlalpha.engines`、`nlalpha.strategies`、`nlalpha.capabilities`、`nlalpha.data` 与 `nlalpha.capability_server` 入口点。`yfinance` 必需，`tushare` 可选。

`serve` 导入所选服务的 `main` 并在当前进程中运行它；服务读取 `NLALPHA_HOST` 与 `NLALPHA_PORT`。

`up` 以独立进程启动四个 MCP 服务以及一个一次性 Redis。运行状态写入 `~/.nlalpha`（`run.json`、日志、工作区与回测 SQLite 任务库），并在 `data`/`backtest` 的 `/ready` 与 `strategy`/`capability` 的 `/health` 就绪后才报告成功。

| 选项 | 默认值 | 用途 |
|---|---|---|
| `--provider` | `yfinance` | 数据提供方；`tushare` 需要 `china` 附加项与 `TUSHARE_TOKEN`。 |
| `--redis-url` | 一次性 Redis | 使用已有 Redis，而不是新启动一个。 |
| `--data-port` | `8001` | 数据服务端口。 |
| `--strategy-port` | `8002` | 策略服务端口。 |
| `--capability-port` | `8003` | 能力服务端口。 |
| `--backtest-port` | `8004` | 回测服务端口。 |
| `--state-dir` | `~/.nlalpha` | 运行状态目录。 |

`down` 停止 `run.json` 中记录的进程，移除由本工具启动的 Redis 容器或进程，并删除状态文件。`status` 输出各服务的端口、进程号、健康状态以及 Redis 可达性。`mcp-config` 在存在 `run.json` 时按其端口输出 MCP 客户端 JSON 配置，否则使用默认端口。

## 附加项

| 附加项 | 内容 |
|---|---|
| `china` | `nlalpha-tushare` |
| `s3` | `nlalpha-data[s3]` 与 `nlalpha-backtest[redis]` |

私有 Vector/statistics 包不属于社区包；请从私有索引显式安装。

## 要求与限制

- `yfinance` 是默认的快速开始提供方，属于非官方接入，可能受上游服务限流影响。
- Tushare 可选，同时需要 `china` 附加项与 `TUSHARE_TOKEN`。
- `up` 优先通过 Docker 启动 Redis，其次在回环地址上使用 `redis-server`。两者都未安装时，请通过 `--redis-url` 指向已有 Redis。
- 本地栈将服务绑定到 `127.0.0.1` 并使用单用户身份，面向开发与快速开始，不是加固的多用户部署。
- 平台适配器不包含在内；它承载平台身份、沙箱与部署语义。
- 领域契约与逻辑位于 `nlalpha-core` 与各服务包中。`nlalpha` 分发仅提供 `nlalpha.cli` 命名空间与依赖版本锁定。

## 开发

```bash
python -m venv .venv
. .venv/bin/activate
pip install pytest
PYTHONPATH=src pytest tests -q
pip install -e . --no-deps
nlalpha doctor
```

`doctor` 会报告缺失的必需分发包和缺失的插件 entry point 组；在所有 pin 包安装完成前以非零码退出。
