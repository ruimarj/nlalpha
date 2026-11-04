"""Runtime state and service launch helpers for the local NLAlpha stack."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .process import http_ok, pid_alive, terminate_pids
from .redis_support import stop_redis
from .serve import SERVICES

DEFAULT_PORTS = {"data": 8001, "strategy": 8002, "capability": 8003, "backtest": 8004}
HEALTH_PATHS = {"data": "/ready", "strategy": "/health", "capability": "/health", "backtest": "/ready"}
SERVICE_START_TIMEOUT = 60.0


def resolve_state_dir(raw: str) -> Path:
    """Return the absolute state directory for a CLI value."""
    return Path(raw).expanduser().resolve()


def read_state(path: Path):
    """Return run state from disk, or None when it is absent or invalid."""
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def write_state(path: Path, state: dict) -> None:
    """Write run state as JSON."""
    path.write_text(json.dumps(state, indent=2) + "\n")


def state_pids(state: dict) -> list:
    """Return every process id recorded in run state."""
    pids = []
    for service in state.get("services", {}).values():
        pid = service.get("pid")
        if isinstance(pid, int):
            pids.append(pid)
    redis = state.get("redis") or {}
    if isinstance(redis.get("pid"), int):
        pids.append(redis["pid"])
    return pids


def state_has_running(state: dict) -> bool:
    """Return whether any process in run state is still alive."""
    return any(pid_alive(pid) for pid in state_pids(state))


def build_environment(provider: str, redis_url: str, state_dir: Path) -> dict:
    """Build the common service environment for a local run."""
    environment = os.environ.copy()
    environment.update({
        "NLALPHA_HOST": "127.0.0.1",
        "NLALPHA_DATA_PROVIDER": provider,
        "NLALPHA_ARTIFACT_BACKEND": "redis",
        "NLALPHA_ARTIFACT_REDIS_URL": redis_url,
        "NLALPHA_IDENTITY_MODE": "single-user",
        "NLALPHA_WORKSPACE_DIR": str(state_dir / "workspace"),
        "JOB_STORE_DSN": f"sqlite:///{state_dir / 'backtest-jobs.db'}",
    })
    return environment


def service_environment(environment: dict, port: int) -> dict:
    """Return a copy of the common environment with the service port set."""
    service = dict(environment)
    service["NLALPHA_PORT"] = str(port)
    return service


def start_service(module: str, environment: dict, log_path: Path):
    """Start one service process with output redirected to a log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as log:
        return subprocess.Popen(
            [sys.executable, "-c", f"from {module} import main; main()"],
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def wait_for_services(ports: dict, timeout: float = SERVICE_START_TIMEOUT) -> list:
    """Return service names that did not become healthy before the deadline."""
    pending = set(ports)
    deadline = time.monotonic() + timeout
    while pending and time.monotonic() < deadline:
        for name in sorted(pending):
            url = f"http://127.0.0.1:{ports[name]}{HEALTH_PATHS[name]}"
            if http_ok(url, timeout=1.0):
                pending.discard(name)
        if pending:
            time.sleep(0.5)
    return sorted(pending)


def cleanup(processes: dict, redis) -> None:
    """Terminate started services and stop owned Redis."""
    terminate_pids([process.pid for process in processes.values()])
    stop_redis(redis)


def ports_from_args(args) -> dict:
    """Read service ports from parsed CLI arguments."""
    return {name: getattr(args, f"{name}_port") for name in SERVICES}


def mcp_servers(ports: dict) -> dict:
    """Build MCP client configuration for the local services."""
    return {
        "mcpServers": {
            f"nlalpha-{name}": {"url": f"http://127.0.0.1:{ports[name]}/sse"}
            for name in SERVICES
        }
    }


def ports_from_state(state) -> dict:
    """Return service ports from run state, falling back to defaults."""
    ports = dict(DEFAULT_PORTS)
    if not state:
        return ports
    for name, entry in state.get("services", {}).items():
        if name in ports and isinstance(entry.get("port"), int):
            ports[name] = entry["port"]
    return ports
