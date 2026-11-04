"""Start, stop, and inspect the local NLAlpha MCP service stack."""

import json
import os
import sys

from .doctor import distribution_installed
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


def run_up(args) -> int:
    """Start the four backtest MCP services and a disposable Redis."""
    state_dir = resolve_state_dir(args.state_dir)
    run_path = state_dir / "run.json"
    state = read_state(run_path)
    if state and state_has_running(state):
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
    if args.provider == "tushare":
        if not os.environ.get("TUSHARE_TOKEN"):
            print("--provider tushare requires TUSHARE_TOKEN", file=sys.stderr)
            return 1
        if not distribution_installed("nlalpha-tushare"):
            print('--provider tushare requires the china extra: pip install "nlalpha[china]"', file=sys.stderr)
            return 1
    state_dir.mkdir(parents=True, exist_ok=True)
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
    print("NLAlpha services:")
    for name in SERVICES:
        entry = services.get(name, {})
        port = entry.get("port", DEFAULT_PORTS[name])
        pid = entry.get("pid")
        url = f"http://127.0.0.1:{port}{HEALTH_PATHS[name]}"
        health = "healthy" if http_ok(url) else "unreachable"
        print(f"  {name:<10} port {port:<5} pid {str(pid):<8} {health}")
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
