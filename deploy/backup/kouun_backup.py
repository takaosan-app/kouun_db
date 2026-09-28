"""Back up the kouun_db database, settings and raw files with restic.

Run from kouun-backup.service. The last stdout line is picked up by
kouun_notify.py as the notification summary.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "runtime" / "raw"
SETTINGS_FILES = (PROJECT_DIR / ".env", PROJECT_DIR / ".env.notify")
STAGING_DIR = Path.home() / "kouun-backup-staging"
RESTIC_ENV_FILE = Path.home() / ".config" / "restic" / "kouun.env"
KEEP_DAILY = 7
KEEP_WEEKLY = 4


def main() -> int:
    started = time.monotonic()
    env = _restic_environment()

    _prepare_staging()
    dump_bytes = _dump_database(STAGING_DIR / "kouun.dump")
    _copy_settings(STAGING_DIR / "settings")

    backup = _restic_backup(env)
    _run(
        [
            "restic", "forget",
            "--keep-daily", str(KEEP_DAILY),
            "--keep-weekly", str(KEEP_WEEKLY),
            "--prune",
        ],
        env,
    )
    _run(["restic", "check"], env)
    snapshots = json.loads(_run(["restic", "snapshots", "--json"], env))

    print(
        json.dumps(
            {
                "status": "succeeded",
                "mode": "backup",
                "snapshot_id": backup["snapshot_id"][:8],
                "dump_bytes": dump_bytes,
                "files_new": backup["files_new"],
                "files_changed": backup["files_changed"],
                "data_added_bytes": backup["data_added"],
                "total_bytes_processed": backup["total_bytes_processed"],
                "snapshots": len(snapshots),
                "duration_seconds": round(time.monotonic() - started),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _restic_environment() -> dict[str, str]:
    env = dict(os.environ)

    for line in RESTIC_ENV_FILE.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.strip().partition("=")

        if separator and not key.startswith("#"):
            env[key] = value

    return env


def _prepare_staging() -> None:
    STAGING_DIR.mkdir(mode=0o700, exist_ok=True)
    STAGING_DIR.chmod(0o700)


def _dump_database(path: Path) -> int:
    # Write to a temporary file so a failed dump never replaces the last good one.
    temporary = path.with_suffix(".dump.tmp")

    with temporary.open("wb") as output:
        completed = subprocess.run(
            [
                "docker", "compose", "-f", "compose.yml",
                "exec", "-T", "db", "sh", "-c",
                'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                "-Fc -n weather -n analysis",
            ],
            cwd=PROJECT_DIR,
            stdout=output,
        )

    if completed.returncode != 0:
        raise SystemExit(f"pg_dump failed with exit status {completed.returncode}")

    size = temporary.stat().st_size

    if size == 0:
        raise SystemExit("pg_dump produced an empty file")

    temporary.chmod(0o600)
    temporary.replace(path)
    return size


def _copy_settings(directory: Path) -> None:
    directory.mkdir(mode=0o700, exist_ok=True)

    for source in SETTINGS_FILES:
        target = directory / source.name
        shutil.copy2(source, target)
        target.chmod(0o600)


def _restic_backup(env: dict[str, str]) -> dict[str, Any]:
    output = _run(
        [
            "restic", "backup", "--json", "--tag", "daily",
            str(STAGING_DIR), str(RAW_DIR),
        ],
        env,
    )

    for line in output.splitlines():
        message = json.loads(line)

        if message.get("message_type") == "summary":
            return message

    raise SystemExit("restic backup did not report a summary")


def _run(command: list[str], env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        # Keep the reason in the journal so it appears in log_tail.
        print(completed.stderr, file=sys.stderr, end="")
        raise SystemExit(
            f"{' '.join(command[:2])} failed with exit status {completed.returncode}"
        )

    return completed.stdout


if __name__ == "__main__":
    raise SystemExit(main())
