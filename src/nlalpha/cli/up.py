"""Start, stop, and inspect the local NLAlpha MCP service stack."""

import json
import os
from pathlib import Path
import sys

from .doctor import distribution_installed
from .docker_support import (
    COMPOSE_FILENAME,
    compose_down,
    compose_logs,
    compose_running,
    compose_up,
    write_compose,
)
from .errors import UpError
from .process import http_ok, log_tail, port_free, terminate_pids
from .redis_support import ensure_redis, redis_reachable, stop_redis
from .runtime import (
    DEFAULT_PORTS,
    HEALTH_PATHS,
    build_environment,
    cleanup,
    mcp_servers,
    ports_from_args,
    ports_from_state,
    read_state,
    resolve_state_dir,
    service_environment,
    start_service,
    state_has_running,
    wait_for_services,
    write_state,
)
from .serve import SERVICES


def _state_running(state) -> bool:
    """Return whether run state describes live services."""
    if not state:
        return False
    if state.get("mode") == "docker":
        compose_path = state.get("compose_path")
        if not compose_path:
            return True
        return compose_running(Path(compose_path))
    return state_has_running(state)


def run_up(args) -> int:
    """Start the four backtest MCP services with Compose or local processes."""
    state_dir = resolve_state_dir(args.state_dir)
    run_path = state_dir / "run.json"
    state = read_state(run_path)
    try:
        running = _state_running(state)
    except UpError as exc:
        print(f"nlalpha up failed: {exc}", file=sys.stderr)
        return 1
    if running:
        print("nlalpha is already running; run `nlalpha down` first", file=sys.stderr)
        return 1
    run_path.unlink(missing_ok=True)
    ports = ports_from_args(args)
    if len(set(ports.values())) != len(ports):
        print("service ports must be distinct", file=sys.stderr)
        return 1
    busy = [f"{name}:{port}" for name, port in ports.items() if not port_free(port)]
    if busy:
        print(f"ports already in use: {', '.join(busy)}", file=sys.stderr)
        return 1
    if args.docker:
        return _start_docker(args, state_dir, run_path, ports)
    return _start_local(args, state_dir, run_path, ports)


def _start_docker(args, state_dir: Path, run_path: Path, ports: dict) -> int:
    """Start the stack with Docker Compose and record its state."""
    if args.redis_url:
        print("--redis-url is not used with --docker; Redis runs in Compose", file=sys.stderr)
        return 1
    if args.provider == "tushare" and not os.environ.get("TUSHARE_TOKEN"):
        print("--provider tushare requires TUSHARE_TOKEN", file=sys.stderr)
        return 1
    state_dir.mkdir(parents=True, exist_ok=True)
    compose_path = state_dir / COMPOSE_FILENAME
    write_compose(compose_path, args.image, ports, args.provider)
    try:
        compose_up(compose_path)
    except UpError as exc:
        print(f"nlalpha up failed: {exc}", file=sys.stderr)
        return 1
    try:
        unhealthy = wait_for_services(ports)
    except BaseException:
        try:
            compose_down(compose_path)
        except UpError:
            pass
        raise
    if unhealthy:
        for name in unhealthy:
            print(f"nlalpha {name} did not become healthy", file=sys.stderr)
        logs = compose_logs(compose_path)
        if logs:
            print(logs, file=sys.stderr)
        try:
            compose_down(compose_path)
        except UpError as exc:
            print(f"nlalpha cleanup failed: {exc}", file=sys.stderr)
        return 1
    state = {
        "mode": "docker",
        "provider": args.provider,
        "image": args.image,
        "compose_path": str(compose_path),
        "ports": ports,
        "redis": {"url": "redis://redis:6379/0", "managed_by": "compose"},
        "services": {
            name: {
                "port": ports[name],
                "url": f"http://127.0.0.1:{ports[name]}",
                "health": HEALTH_PATHS[name],
            }
            for name in SERVICES
        },
    }
    write_state(run_path, state)
    print("NLAlpha services are running (Docker Compose):")
    for name in SERVICES:
        print(f"  {name:<10} http://127.0.0.1:{ports[name]}")
    print(f"Image: {args.image}")
    print(f"Compose: {compose_path}")
    print("Next: `nlalpha mcp-config` prints MCP client configuration")
    return 0


def _start_local(args, state_dir: Path, run_path: Path, ports: dict) -> int:
    """Start the stack as local Python processes and record their state."""
    if args.provider == "tushare":
        if not os.environ.get("TUSHARE_TOKEN"):
            print("--provider tushare requires TUSHARE_TOKEN", file=sys.stderr)
            return 1
        if not distribution_installed("nlalpha-tushare"):
            print('--provider tushare requires the china extra: pip install "nlalpha[china]"', file=sys.stderr)
            return 1
    (state_dir / "logs").mkdir(parents=True, exist_ok=True)
    (state_dir / "workspace").mkdir(parents=True, exist_ok=True)
    processes = {}
    redis = None
    try:
        redis = ensure_redis(args.redis_url, state_dir)
        environment = build_environment(args.provider, redis["url"], state_dir)
        for name, module in SERVICES.items():
            environment_for_service = service_environment(environment, ports[name])
            processes[name] = start_service(
                module, environment_for_service, state_dir / "logs" / f"{name}.log"
            )
        unhealthy = wait_for_services(ports)
        if unhealthy:
            for name in unhealthy:
                print(f"nlalpha {name} did not become healthy:", file=sys.stderr)
                print(log_tail(state_dir / "logs" / f"{name}.log"), file=sys.stderr)
            raise UpError(f"services did not become healthy: {', '.join(unhealthy)}")
    except UpError as exc:
        cleanup(processes, redis)
        print(f"nlalpha up failed: {exc}", file=sys.stderr)
        return 1
    except BaseException:
        cleanup(processes, redis)
        raise
    state = {
        "mode": "local",
        "provider": args.provider,
        "redis": redis,
        "services": {
            name: {
                "pid": processes[name].pid,
                "port": ports[name],
                "url": f"http://127.0.0.1:{ports[name]}",
                "health": HEALTH_PATHS[name],
            }
            for name in SERVICES
        },
    }
    write_state(run_path, state)
    print("NLAlpha services are running:")
    for name in SERVICES:
        print(f"  {name:<10} http://127.0.0.1:{ports[name]}  (pid {processes[name].pid})")
    print(f"Redis: {redis['url']}")
    print("Next: `nlalpha mcp-config` prints MCP client configuration")
    return 0


def run_down(args) -> int:
    """Stop services recorded in run state and remove the state file."""
    state_dir = resolve_state_dir(args.state_dir)
    run_path = state_dir / "run.json"
    state = read_state(run_path)
    if not state:
        print("nlalpha is not running")
        return 0
    if state.get("mode") == "docker":
        compose_path = state.get("compose_path")
        if not compose_path:
            print("nlalpha has no Docker Compose path in its state", file=sys.stderr)
            return 1
        try:
            compose_down(Path(compose_path))
        except UpError as exc:
            print(f"nlalpha down failed: {exc}", file=sys.stderr)
            return 1
        run_path.unlink(missing_ok=True)
        print("nlalpha stopped")
        return 0
    pids = [service.get("pid") for service in state.get("services", {}).values()]
    terminate_pids([pid for pid in pids if isinstance(pid, int)])
    stop_redis(state.get("redis"))
    run_path.unlink(missing_ok=True)
    print("nlalpha stopped")
    return 0


def run_status(args) -> int:
    """Print service processes, ports, health, and Redis status."""
    state_dir = resolve_state_dir(args.state_dir)
    state = read_state(state_dir / "run.json")
    services = (state or {}).get("services", {})
    mode = (state or {}).get("mode", "local")
    print("NLAlpha services:")
    for name in SERVICES:
        entry = services.get(name, {})
        port = entry.get("port", DEFAULT_PORTS[name])
        url = f"http://127.0.0.1:{port}{HEALTH_PATHS[name]}"
        health = "healthy" if http_ok(url) else "unreachable"
        if mode == "docker":
            print(f"  {name:<10} port {port:<5} {health}")
        else:
            pid = entry.get("pid")
            print(f"  {name:<10} port {port:<5} pid {str(pid):<8} {health}")
    if mode == "docker":
        print("Redis: managed by Docker Compose")
        if state and state.get("image"):
            print(f"Image: {state['image']}")
        return 0
    redis = (state or {}).get("redis")
    if redis:
        reachable = "reachable" if redis_reachable(redis["url"]) else "unreachable"
        ownership = "managed" if redis.get("owned") else "external"
        print(f"Redis: {redis['url']} ({ownership}, {reachable})")
    else:
        print("Redis: not managed by nlalpha")
    return 0


def run_mcp_config(args) -> int:
    """Print MCP client configuration for the local services."""
    state_dir = resolve_state_dir(args.state_dir)
    state = read_state(state_dir / "run.json")
    print(json.dumps(mcp_servers(ports_from_state(state)), indent=2))
    return 0
