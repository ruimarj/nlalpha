"""Disposable Redis management for the local NLAlpha stack."""

from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import urllib.parse

from .errors import UpError
from .process import find_free_port, terminate_pids, wait_tcp

REDIS_START_TIMEOUT = 30.0


def ensure_redis(redis_url, state_dir: Path) -> dict:
    """Return Redis connection state, starting a disposable instance when needed."""
    if redis_url:
        return {"url": redis_url, "owned": False, "container": None, "pid": None}
    port = find_free_port()
    docker = shutil.which("docker")
    if docker:
        container = f"nlalpha-redis-{secrets.token_hex(4)}"
        command = [
            docker, "run", "-d", "--rm", "--name", container,
            "-p", f"127.0.0.1:{port}:6379", "redis:7-alpine",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise UpError(f"failed to start Redis container: {result.stderr.strip()}")
        if not wait_tcp("127.0.0.1", port, REDIS_START_TIMEOUT):
            stop_redis({"owned": True, "container": container, "pid": None})
            raise UpError("Redis container did not become ready")
        url = f"redis://127.0.0.1:{port}/0"
        return {"url": url, "owned": True, "container": container, "pid": None}
    redis_server = shutil.which("redis-server")
    if redis_server:
        logs = state_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        data = state_dir / "redis"
        data.mkdir(parents=True, exist_ok=True)
        command = [
            redis_server, "--port", str(port), "--bind", "127.0.0.1",
            "--save", "", "--appendonly", "no", "--dir", str(data),
        ]
        with open(logs / "redis.log", "ab") as log:
            process = subprocess.Popen(
                command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
        if not wait_tcp("127.0.0.1", port, REDIS_START_TIMEOUT):
            terminate_pids([process.pid])
            raise UpError("Redis server did not become ready")
        url = f"redis://127.0.0.1:{port}/0"
        return {"url": url, "owned": True, "container": None, "pid": process.pid}
    raise UpError("Redis is required: install Docker or redis-server, or pass --redis-url")


def stop_redis(redis) -> None:
    """Stop a Redis instance owned by the current run."""
    if not redis or not redis.get("owned"):
        return
    container = redis.get("container")
    if container:
        docker = shutil.which("docker")
        if docker:
            subprocess.run([docker, "rm", "-f", container], capture_output=True, text=True)
        return
    pid = redis.get("pid")
    if isinstance(pid, int):
        terminate_pids([pid])


def redis_reachable(url: str) -> bool:
    """Return whether a Redis URL accepts TCP connections."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False
