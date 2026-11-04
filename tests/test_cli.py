"""CLI behavior tests for the NLAlpha bundle."""

from contextlib import redirect_stdout
from importlib.metadata import PackageNotFoundError
from io import StringIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from nlalpha.cli import doctor, main, redis_support, runtime, serve, up
from nlalpha.cli.errors import UpError


def _entry_groups(**groups):
    def resolve(*, group):
        return [SimpleNamespace(name=name) for name in groups.get(group, [])]
    return resolve


ALL_ENTRY_GROUPS = {
    "nlalpha.engines": ["cta"],
    "nlalpha.strategies": ["cta"],
    "nlalpha.capabilities": ["cta"],
    "nlalpha.data": ["yfinance"],
    "nlalpha.capability_server": ["cta"],
}


def _up_args(state_dir, **overrides):
    values = {
        "state_dir": str(state_dir),
        "provider": "yfinance",
        "redis_url": None,
        "data_port": 8001,
        "strategy_port": 8002,
        "capability_port": 8003,
        "backtest_port": 8004,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_required_distributions_and_entry_points(self):
        groups = dict(ALL_ENTRY_GROUPS, **{"nlalpha.data": ["yfinance", "tushare"]})
        with patch.object(doctor, "version", return_value="1.0.0"), \
                patch.object(doctor, "entry_points", side_effect=_entry_groups(**groups)), \
                patch.dict(os.environ, {"TUSHARE_TOKEN": "token"}):
            self.assertEqual(doctor.run_doctor(None), 0)

    def test_doctor_accepts_missing_optional_tushare(self):
        def version_for(name):
            if name == "nlalpha-tushare":
                raise PackageNotFoundError(name)
            return "1.0.0"

        output = StringIO()
        with patch.object(doctor, "version", side_effect=version_for), \
                patch.object(doctor, "entry_points", side_effect=_entry_groups(**ALL_ENTRY_GROUPS)), \
                patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            self.assertEqual(doctor.run_doctor(None), 0)
        self.assertIn("nlalpha-tushare not installed (optional)", output.getvalue())
        self.assertNotIn("TUSHARE_TOKEN", output.getvalue())

    def test_doctor_fails_when_yfinance_is_missing(self):
        def version_for(name):
            if name == "nlalpha-yfinance":
                raise PackageNotFoundError(name)
            return "1.0.0"

        groups = dict(ALL_ENTRY_GROUPS, **{"nlalpha.data": ["tushare"]})
        with patch.object(doctor, "version", side_effect=version_for), \
                patch.object(doctor, "entry_points", side_effect=_entry_groups(**groups)), \
                patch.dict(os.environ, {"TUSHARE_TOKEN": "token"}):
            self.assertEqual(doctor.run_doctor(None), 1)

    def test_doctor_fails_without_a_required_data_provider(self):
        groups = dict(ALL_ENTRY_GROUPS, **{"nlalpha.data": []})
        with patch.object(doctor, "version", return_value="1.0.0"), \
                patch.object(doctor, "entry_points", side_effect=_entry_groups(**groups)), \
                patch.dict(os.environ, {"TUSHARE_TOKEN": "token"}):
            self.assertEqual(doctor.run_doctor(None), 1)

    def test_doctor_warns_about_token_only_when_tushare_is_available(self):
        groups = dict(ALL_ENTRY_GROUPS, **{"nlalpha.data": ["yfinance", "tushare"]})
        output = StringIO()
        with patch.object(doctor, "version", return_value="1.0.0"), \
                patch.object(doctor, "entry_points", side_effect=_entry_groups(**groups)), \
                patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            self.assertEqual(doctor.run_doctor(None), 0)
        self.assertIn("TUSHARE_TOKEN", output.getvalue())


class ServeTests(unittest.TestCase):
    def test_serve_imports_selected_service_and_runs_main(self):
        module = SimpleNamespace(main=Mock())
        with patch.object(serve, "import_module", return_value=module) as importer:
            self.assertEqual(serve.run_serve(SimpleNamespace(service="data")), 0)
        importer.assert_called_once_with("nlalpha_data.server")
        module.main.assert_called_once_with()


class MainTests(unittest.TestCase):
    def test_main_dispatches_doctor_and_serve(self):
        with patch.object(main, "run_doctor", return_value=7) as doctor_handler:
            self.assertEqual(main.main(["doctor"]), 7)
        doctor_handler.assert_called_once()
        with patch.object(main, "run_serve", return_value=8) as serve_handler:
            self.assertEqual(main.main(["serve", "capability"]), 8)
        self.assertEqual(serve_handler.call_args.args[0].service, "capability")

    def test_main_accepts_up_options(self):
        with patch.object(main, "run_up", return_value=3) as handler:
            self.assertEqual(
                main.main([
                    "up", "--provider", "tushare",
                    "--redis-url", "redis://localhost:6379/0",
                    "--data-port", "8101",
                ]),
                3,
            )
        args = handler.call_args.args[0]
        self.assertEqual(args.provider, "tushare")
        self.assertEqual(args.redis_url, "redis://localhost:6379/0")
        self.assertEqual(args.data_port, 8101)
        self.assertEqual(args.strategy_port, 8002)
        self.assertEqual(args.capability_port, 8003)
        self.assertEqual(args.backtest_port, 8004)
        self.assertEqual(args.state_dir, "~/.nlalpha")

    def test_main_dispatches_lifecycle_commands(self):
        for command, handler_name in (
            ("down", "run_down"),
            ("status", "run_status"),
            ("mcp-config", "run_mcp_config"),
        ):
            with patch.object(main, handler_name, return_value=4) as handler:
                self.assertEqual(main.main([command, "--state-dir", "/tmp/nlalpha"]), 4)
            self.assertEqual(handler.call_args.args[0].state_dir, "/tmp/nlalpha")

    def test_main_requires_a_subcommand(self):
        with self.assertRaises(SystemExit):
            main.main([])


class EnvironmentTests(unittest.TestCase):
    def test_build_environment_sets_shared_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            environment = runtime.build_environment("yfinance", "redis://127.0.0.1:6399/0", state_dir)
        self.assertEqual(environment["NLALPHA_HOST"], "127.0.0.1")
        self.assertEqual(environment["NLALPHA_DATA_PROVIDER"], "yfinance")
        self.assertEqual(environment["NLALPHA_ARTIFACT_BACKEND"], "redis")
        self.assertEqual(environment["NLALPHA_ARTIFACT_REDIS_URL"], "redis://127.0.0.1:6399/0")
        self.assertEqual(environment["NLALPHA_IDENTITY_MODE"], "single-user")
        self.assertEqual(environment["NLALPHA_WORKSPACE_DIR"], str(state_dir / "workspace"))
        self.assertEqual(environment["JOB_STORE_DSN"], f"sqlite:///{state_dir / 'backtest-jobs.db'}")
        self.assertNotIn("NLALPHA_PORT", environment)

    def test_service_environment_sets_the_service_port(self):
        base = {"NLALPHA_HOST": "127.0.0.1"}
        service = runtime.service_environment(base, 8102)
        self.assertEqual(service["NLALPHA_PORT"], "8102")
        self.assertNotIn("NLALPHA_PORT", base)

    def test_mcp_servers_use_default_urls(self):
        self.assertEqual(runtime.mcp_servers(runtime.DEFAULT_PORTS), {
            "mcpServers": {
                "nlalpha-data": {"url": "http://127.0.0.1:8001/sse"},
                "nlalpha-strategy": {"url": "http://127.0.0.1:8002/sse"},
                "nlalpha-capability": {"url": "http://127.0.0.1:8003/sse"},
                "nlalpha-backtest": {"url": "http://127.0.0.1:8004/sse"},
            }
        })


class McpConfigTests(unittest.TestCase):
    def test_mcp_config_uses_ports_from_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "services": {
                    "data": {"pid": 1, "port": 9001},
                    "strategy": {"pid": 2, "port": 9002},
                    "capability": {"pid": 3, "port": 9003},
                    "backtest": {"pid": 4, "port": 9004},
                }
            }
            runtime.write_state(Path(tmp) / "run.json", state)
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(up.run_mcp_config(SimpleNamespace(state_dir=tmp)), 0)
        config = json.loads(output.getvalue())
        self.assertEqual(config["mcpServers"]["nlalpha-data"]["url"], "http://127.0.0.1:9001/sse")
        self.assertEqual(config["mcpServers"]["nlalpha-backtest"]["url"], "http://127.0.0.1:9004/sse")

    def test_mcp_config_uses_defaults_without_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(up.run_mcp_config(SimpleNamespace(state_dir=tmp)), 0)
        config = json.loads(output.getvalue())
        self.assertEqual(config["mcpServers"]["nlalpha-capability"]["url"], "http://127.0.0.1:8003/sse")


class RedisTests(unittest.TestCase):
    def test_explicit_redis_url_is_not_owned(self):
        with tempfile.TemporaryDirectory() as tmp:
            redis = redis_support.ensure_redis("redis://example:6379/0", Path(tmp))
        self.assertEqual(redis, {
            "url": "redis://example:6379/0",
            "owned": False,
            "container": None,
            "pid": None,
        })

    def test_missing_redis_binaries_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(redis_support.shutil, "which", return_value=None):
                with self.assertRaises(UpError):
                    redis_support.ensure_redis(None, Path(tmp))

    def test_docker_starts_a_disposable_redis(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(redis_support.shutil, "which", side_effect=lambda name: "/usr/bin/docker" if name == "docker" else None), \
                    patch.object(redis_support, "find_free_port", return_value=6390), \
                    patch.object(redis_support, "wait_tcp", return_value=True), \
                    patch.object(redis_support.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="id\n", stderr="")) as runner:
                redis = redis_support.ensure_redis(None, Path(tmp))
        self.assertEqual(redis["url"], "redis://127.0.0.1:6390/0")
        self.assertTrue(redis["owned"])
        self.assertTrue(redis["container"].startswith("nlalpha-redis-"))
        command = runner.call_args.args[0]
        self.assertIn("redis:7-alpine", command)
        self.assertIn("127.0.0.1:6390:6379", command)


class RunUpTests(unittest.TestCase):
    def test_refuses_when_state_has_running_processes(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {"services": {"data": {"pid": 111}}, "redis": {"pid": 222}}
            runtime.write_state(Path(tmp) / "run.json", state)
            with patch.object(runtime, "pid_alive", return_value=True), \
                    patch.object(up, "ensure_redis") as redis, \
                    patch.object(up, "start_service") as starter:
                self.assertEqual(up.run_up(_up_args(tmp)), 1)
        redis.assert_not_called()
        starter.assert_not_called()

    def test_tushare_provider_requires_a_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(up, "port_free", return_value=True), \
                    patch.object(up, "distribution_installed", return_value=True), \
                    patch.object(up, "ensure_redis") as redis, \
                    patch.dict(os.environ, {}, clear=True):
                self.assertEqual(up.run_up(_up_args(tmp, provider="tushare")), 1)
        redis.assert_not_called()

    def test_tushare_provider_requires_the_china_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(up, "port_free", return_value=True), \
                    patch.object(up, "distribution_installed", return_value=False), \
                    patch.object(up, "ensure_redis") as redis, \
                    patch.dict(os.environ, {"TUSHARE_TOKEN": "token"}):
                self.assertEqual(up.run_up(_up_args(tmp, provider="tushare")), 1)
        redis.assert_not_called()

    def test_busy_ports_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(up, "port_free", return_value=False), \
                    patch.object(up, "ensure_redis") as redis:
                self.assertEqual(up.run_up(_up_args(tmp)), 1)
        redis.assert_not_called()

    def test_successful_start_writes_run_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            pids = {}

            def start_service(module, environment, log_path):
                pids[module] = 1000 + len(pids)
                return SimpleNamespace(pid=pids[module])

            redis = {"url": "redis://127.0.0.1:6399/0", "owned": True, "container": None, "pid": 999}
            output = StringIO()
            with patch.object(up, "port_free", return_value=True), \
                    patch.object(up, "ensure_redis", return_value=redis), \
                    patch.object(up, "start_service", side_effect=start_service), \
                    patch.object(up, "wait_for_services", return_value=[]), \
                    redirect_stdout(output):
                self.assertEqual(up.run_up(_up_args(tmp)), 0)
            state = json.loads((Path(tmp) / "run.json").read_text())
        self.assertEqual(state["provider"], "yfinance")
        self.assertEqual(state["redis"], redis)
        self.assertEqual(state["services"]["data"]["pid"], 1000)
        self.assertEqual(state["services"]["data"]["port"], 8001)
        self.assertEqual(state["services"]["backtest"]["url"], "http://127.0.0.1:8004")
        self.assertIn("nlalpha mcp-config", output.getvalue())


class RunDownTests(unittest.TestCase):
    def test_down_terminates_services_and_removes_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "services": {
                    "data": {"pid": 111, "port": 8001},
                    "strategy": {"pid": 112, "port": 8002},
                },
                "redis": {"url": "redis://127.0.0.1:6399/0", "owned": True, "container": "redis", "pid": 222},
            }
            run_path = Path(tmp) / "run.json"
            runtime.write_state(run_path, state)
            with patch.object(up, "terminate_pids") as terminate, \
                    patch.object(up, "stop_redis") as stop_redis:
                self.assertEqual(up.run_down(SimpleNamespace(state_dir=tmp)), 0)
            self.assertFalse(run_path.exists())
        terminate.assert_called_once_with([111, 112])
        stop_redis.assert_called_once_with(state["redis"])

    def test_down_is_idempotent_without_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = StringIO()
            with patch.object(up, "terminate_pids") as terminate, \
                    patch.object(up, "stop_redis") as stop_redis, \
                    redirect_stdout(output):
                self.assertEqual(up.run_down(SimpleNamespace(state_dir=tmp)), 0)
        terminate.assert_not_called()
        stop_redis.assert_not_called()
        self.assertIn("not running", output.getvalue())


class RunStatusTests(unittest.TestCase):
    def test_status_reports_services_and_redis(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "services": {"data": {"pid": 111, "port": 9001}},
                "redis": {"url": "redis://127.0.0.1:6399/0", "owned": True, "container": None, "pid": 999},
            }
            runtime.write_state(Path(tmp) / "run.json", state)
            output = StringIO()
            with patch.object(up, "http_ok", return_value=True), \
                    patch.object(up, "redis_reachable", return_value=True), \
                    redirect_stdout(output):
                self.assertEqual(up.run_status(SimpleNamespace(state_dir=tmp)), 0)
        text = output.getvalue()
        self.assertIn("data", text)
        self.assertIn("port 9001", text)
        self.assertIn("healthy", text)
        self.assertIn("Redis: redis://127.0.0.1:6399/0 (managed, reachable)", text)

    def test_status_without_state_uses_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = StringIO()
            with patch.object(up, "http_ok", return_value=False), redirect_stdout(output):
                self.assertEqual(up.run_status(SimpleNamespace(state_dir=tmp)), 0)
        text = output.getvalue()
        self.assertIn("port 8001", text)
        self.assertIn("Redis: not managed by nlalpha", text)


class RunStateTests(unittest.TestCase):
    def test_state_has_running_processes(self):
        state = {"services": {"data": {"pid": 111}}, "redis": {"pid": 222}}
        with patch.object(runtime, "pid_alive", side_effect=lambda pid: pid == 222):
            self.assertTrue(runtime.state_has_running(state))

    def test_stale_state_has_no_running_processes(self):
        state = {"services": {"data": {"pid": 111}}, "redis": {"pid": 222}}
        with patch.object(runtime, "pid_alive", return_value=False):
            self.assertFalse(runtime.state_has_running(state))
