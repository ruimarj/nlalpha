# nlalpha

面向 NLAlpha 社区回测栈的安装即用包。它依赖十个社区分发包，并提供轻量的 `nlalpha` 命令；自身不包含领域逻辑。

## 安装

```bash
uv pip install nlalpha
```

使用为你的环境配置的包索引（例如 `UV_INDEX_URL` 或 `pip --index-url`）。内部部署通过部署环境注入索引；此处不提交任何索引地址。

本包精确 pin 全部十个社区分发包；所有 pin 版本必须能在所配置的索引中解析。

## 命令

```text
nlalpha doctor
nlalpha serve data|strategy|capability|backtest
```

`doctor` 报告已安装分发版本以及发现的 `nlalpha.engines`、`nlalpha.strategies`、`nlalpha.capabilities`、`nlalpha.data` 与 `nlalpha.capability_server` 入口点。`serve` 导入所选服务的 `main` 并在当前进程中运行它；服务读取 `NLALPHA_HOST` 与 `NLALPHA_PORT`。

## 附加项

| 附加项 | 内容 |
|---|---|
| `s3` | `nlalpha-data[s3]` 与 `nlalpha-backtest[redis]` |

私有 Vector/statistics 包不属于社区包；请从私有索引显式安装。

## 边界

- Tushare 需要 `TUSHARE_TOKEN`；安装本包并不授予数据访问权限。
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

`doctor` 会报告缺失的分发包和缺失的插件 entry point 组；在所有 pin 包安装完成前以非零码退出。
