"""Process, HTTP, and socket helpers for the local NLAlpha stack."""

import os
from pathlib import Path
import signal
import socket
import time
import urllib.error
import urllib.request

STOP_TIMEOUT = 10.0


def pid_alive(pid: int) -> bool:
    """Return whether a process id is alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def signal_pid(pid: int, sig: int) -> None:
    """Send a signal to a process, ignoring missing processes."""
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass


def terminate_pids(pids, timeout: float = STOP_TIMEOUT) -> None:
    """Terminate processes with SIGTERM, escalating to SIGKILL after a timeout."""
    alive = [pid for pid in pids if isinstance(pid, int) and pid_alive(pid)]
    for pid in alive:
        signal_pid(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and any(pid_alive(pid) for pid in alive):
        time.sleep(0.2)
    for pid in alive:
        if pid_alive(pid):
            signal_pid(pid, signal.SIGKILL)


def http_ok(url: str, timeout: float = 2.0) -> bool:
    """Return whether an HTTP request succeeds with a 2xx/3xx status."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (OSError, urllib.error.URLError):
        return False


def wait_tcp(host: str, port: int, timeout: float) -> bool:
    """Wait until a TCP endpoint accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def port_free(port: int) -> bool:
    """Return whether a loopback TCP port can be bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def find_free_port() -> int:
    """Return an unused loopback TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def log_tail(path: Path, lines: int = 20) -> str:
    """Return the last lines of a log file."""
    try:
        content = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])
