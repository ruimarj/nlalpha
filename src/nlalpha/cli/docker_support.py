"""Docker Compose rendering and lifecycle helpers for the NLAlpha stack."""

from pathlib import Path
import shutil
import subprocess

from .errors import UpError

DEFAULT_IMAGE = "ghcr.io/ruimarj/nlalpha:0.2.4"
COMPOSE_FILENAME = "compose.yaml"

_COMPOSE_TEMPLATE = """\
name: nlalpha

services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20

  data:
    image: __IMAGE__
    command: ["serve", "data"]
    restart: unless-stopped
    environment:
      NLALPHA_HOST: "0.0.0.0"
      NLALPHA_PORT: "8001"
      NLALPHA_IDENTITY_MODE: "single-user"
      NLALPHA_DATA_PROVIDER: "__PROVIDER__"
      TUSHARE_TOKEN: "${TUSHARE_TOKEN:-}"
      NLALPHA_ARTIFACT_BACKEND: "redis"
      NLALPHA_ARTIFACT_REDIS_URL: "redis://redis:6379/0"
      NLALPHA_WORKSPACE_DIR: "/state/workspace"
    ports:
      - "127.0.0.1:__DATA_PORT__:8001"
    volumes:
      - nlalpha-state:/state
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/ready', timeout=2)"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s

  strategy:
    image: __IMAGE__
    command: ["serve", "strategy"]
    restart: unless-stopped
    environment:
      NLALPHA_HOST: "0.0.0.0"
      NLALPHA_PORT: "8002"
      NLALPHA_IDENTITY_MODE: "single-user"
    ports:
      - "127.0.0.1:__STRATEGY_PORT__:8002"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=2)"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s

  capability:
    image: __IMAGE__
    command: ["serve", "capability"]
    restart: unless-stopped
    environment:
      NLALPHA_HOST: "0.0.0.0"
      NLALPHA_PORT: "8003"
      NLALPHA_IDENTITY_MODE: "single-user"
    ports:
      - "127.0.0.1:__CAPABILITY_PORT__:8003"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=2)"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s

  backtest:
    image: __IMAGE__
    command: ["serve", "backtest"]
    restart: unless-stopped
    environment:
      NLALPHA_HOST: "0.0.0.0"
      NLALPHA_PORT: "8004"
      NLALPHA_IDENTITY_MODE: "single-user"
      NLALPHA_ARTIFACT_BACKEND: "redis"
      NLALPHA_ARTIFACT_REDIS_URL: "redis://redis:6379/0"
      NLALPHA_WORKSPACE_DIR: "/state/workspace"
      JOB_STORE_DSN: "sqlite:////state/backtest-jobs.db"
    ports:
      - "127.0.0.1:__BACKTEST_PORT__:8004"
    volumes:
      - nlalpha-state:/state
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8004/ready', timeout=2)"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s

volumes:
  nlalpha-state:
"""


def render_compose(image: str, ports: dict, provider: str) -> str:
    """Render a Compose file with the selected image, host ports, and provider."""
    values = {"__IMAGE__": image, "__PROVIDER__": provider}
    for name, port in ports.items():
        values[f"__{name.upper()}_PORT__"] = str(port)
    text = _COMPOSE_TEMPLATE
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    return text


def write_compose(path: Path, image: str, ports: dict, provider: str) -> None:
    """Write a rendered Compose file."""
    path.write_text(render_compose(image, ports, provider))


def _docker_binary() -> str:
    """Return the Docker executable or raise when it is unavailable."""
    docker = shutil.which("docker")
    if not docker:
        raise UpError("Docker is required for Docker mode")
    return docker


def run_compose(compose_path: Path, *args) -> subprocess.CompletedProcess:
    """Run one Docker Compose subcommand for a compose file."""
    command = [_docker_binary(), "compose", "-f", str(compose_path), *args]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def compose_up(compose_path: Path) -> None:
    """Start the Compose stack in the background."""
    result = run_compose(compose_path, "up", "-d")
    if result.returncode != 0:
        raise UpError(f"docker compose up failed: {result.stderr.strip()}")


def compose_down(compose_path: Path) -> None:
    """Stop the Compose stack and remove orphan containers."""
    result = run_compose(compose_path, "down", "--remove-orphans")
    if result.returncode != 0:
        raise UpError(f"docker compose down failed: {result.stderr.strip()}")


def compose_running(compose_path: Path) -> bool:
    """Return whether any Compose service is running."""
    result = run_compose(compose_path, "ps", "--status", "running", "-q")
    if result.returncode != 0:
        raise UpError(f"docker compose ps failed: {result.stderr.strip()}")
    return bool(result.stdout.strip())


def compose_logs(compose_path: Path, lines: int = 40) -> str:
    """Return recent Compose service logs."""
    result = run_compose(compose_path, "logs", "--tail", str(lines))
    return (result.stdout or result.stderr).strip()
