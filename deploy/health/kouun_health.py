"""Report host health of the kouun_db server as one JSON line.

Run from kouun-health.service. The last stdout line is picked up by
kouun_notify.py as the notification summary.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "runtime" / "raw"
COMMAND_TIMEOUT_SECONDS = 120


def main() -> int:
    errors: list[str] = []
    report: dict[str, Any] = {
        "status": "succeeded",
        "mode": "health",
        "memory": _collect(_memory, "memory", errors),
        "disk": _collect(_disk, "disk", errors),
        "database_bytes": _collect(_database_bytes, "database_bytes", errors),
        "raw_bytes": _collect(_raw_bytes, "raw_bytes", errors),
        "load": _collect(_load, "load", errors),
        "uptime_hours": _collect(_uptime_hours, "uptime_hours", errors),
        "containers": _collect(_containers, "containers", errors),
        "failed_units": _collect(_failed_units, "failed_units", errors),
    }
    report["errors"] = errors

    if errors:
        report["status"] = "partial"

    print(json.dumps(report, ensure_ascii=False))
    return 0


def _collect(function, name: str, errors: list[str]) -> Any:
    # A metric that could not be read is null, never zero.
    try:
        return function()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        errors.append(f"{name}: {error}")
        return None


def _memory() -> dict[str, int]:
    values = {}

    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        values[key] = int(value.split()[0])  # kB

    total = values["MemTotal"] // 1024
    available = values["MemAvailable"] // 1024
    return {
        "total_mb": total,
        "used_mb": total - available,
        "available_mb": available,
        "swap_total_mb": values["SwapTotal"] // 1024,
        "swap_used_mb": (values["SwapTotal"] - values["SwapFree"]) // 1024,
    }


def _disk() -> dict[str, float]:
    usage = shutil.disk_usage("/")
    gib = 1024 ** 3
    return {
        "total_gb": round(usage.total / gib, 1),
        "used_gb": round(usage.used / gib, 1),
        "free_gb": round(usage.free / gib, 1),
        "used_percent": round(usage.used / usage.total * 100, 1),
    }


def _database_bytes() -> int:
    output = _run(
        [
            "docker", "compose", "-f", "compose.yml",
            "exec", "-T", "db", "sh", "-c",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc '
            '"SELECT pg_database_size(current_database())"',
        ]
    )
    return int(output.strip())


def _raw_bytes() -> int:
    output = _run(["du", "-sb", str(RAW_DIR)])
    return int(output.split()[0])


def _load() -> dict[str, float]:
    one, five, fifteen = os.getloadavg()
    return {
        "1m": round(one, 2),
        "5m": round(five, 2),
        "15m": round(fifteen, 2),
    }


def _uptime_hours() -> float:
    seconds = float(Path("/proc/uptime").read_text().split()[0])
    return round(seconds / 3600, 1)


def _containers() -> list[dict[str, str]]:
    output = _run(
        [
            "docker", "stats", "--no-stream",
            "--format", "{{json .}}",
        ]
    )
    containers = []

    for line in output.splitlines():
        stats = json.loads(line)
        containers.append(
            {
                "name": stats["Name"],
                "cpu": stats["CPUPerc"],
                "memory": stats["MemUsage"],
            }
        )

    return containers


def _failed_units() -> list[str]:
    output = _run(
        [
            "systemctl", "list-units", "--state=failed",
            "--plain", "--no-legend",
        ]
    )
    return [line.split()[0] for line in output.splitlines() if line.strip()]


def _run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        check=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    return completed.stdout


if __name__ == "__main__":
    raise SystemExit(main())
