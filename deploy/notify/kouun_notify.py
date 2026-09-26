"""Notify kouun_db job events from systemd units.

started <job>: called from ExecStartPre of each job unit.
result <job>:  called from kouun-notify@<job>.service via OnSuccess=/OnFailure=.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
SYSLOG_IDENTIFIER = "kouun-notify"
MESSAGE_VERSION = 1
LOG_TAIL_LINES = 20
WEBHOOK_TIMEOUT_SECONDS = 10
SETTINGS_FILE = Path(__file__).resolve().parents[2] / ".env.notify"

JOB_UNITS = {
    "collector": "kouun-collector.service",
    "layers": "kouun-layers.service",
}


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("started", "result"):
        print(
            "usage: kouun_notify.py {started|result} <job>",
            file=sys.stderr,
        )
        return 2

    command, job = argv[1], argv[2]
    unit = JOB_UNITS.get(job)

    if unit is None:
        print(f"unknown job: {job}", file=sys.stderr)
        return 2

    if command == "started":
        message = _base_message(
            "started",
            job,
            unit,
            os.environ.get("INVOCATION_ID") or None,
        )
    else:
        message = _result_message(job, unit)

    priority = "err" if message["event"] == "failed" else "info"
    _journal(json.dumps(message, ensure_ascii=False), priority)
    _post_webhook(message, _load_settings(SETTINGS_FILE))
    return 0


def _base_message(
    event: str,
    job: str,
    unit: str,
    invocation_id: str | None,
) -> dict[str, Any]:
    return {
        "version": MESSAGE_VERSION,
        "event": event,
        "job": job,
        "unit": unit,
        "host": socket.gethostname(),
        "at": datetime.now(JST).isoformat(timespec="seconds"),
        "invocation_id": invocation_id,
    }


def _unit_state(unit: str) -> dict[str, str]:
    completed = subprocess.run(
        [
            "systemctl",
            "show",
            unit,
            "--property=Result,InvocationID,ExecMainStatus",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    state = {}

    for line in completed.stdout.splitlines():
        key, _, value = line.partition("=")
        state[key] = value

    return state


def _result_message(job: str, unit: str) -> dict[str, Any]:
    state = _unit_state(unit)
    service_result = state.get("Result") or "unknown"
    invocation_id = state.get("InvocationID") or None
    succeeded = service_result == "success"

    lines = (
        _read_job_lines(invocation_id)
        if invocation_id
        else []
    )

    message = _base_message(
        "finished" if succeeded else "failed",
        job,
        unit,
        invocation_id,
    )
    message.update(
        {
            "service_result": service_result,
            "exit_status": _exit_status(
                state.get("ExecMainStatus")
            ),
            "summary": _final_json_object(lines),
            "log_tail": (
                None
                if succeeded
                else lines[-LOG_TAIL_LINES:]
            ),
        }
    )
    return message


def _read_job_lines(invocation_id: str) -> list[str]:
    completed = subprocess.run(
        [
            "journalctl",
            f"_SYSTEMD_INVOCATION_ID={invocation_id}",
            "--output=json",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    lines = []

    for raw in completed.stdout.splitlines():
        entry = json.loads(raw)

        if entry.get("SYSLOG_IDENTIFIER") == SYSLOG_IDENTIFIER:
            continue

        text = entry.get("MESSAGE")

        # journald returns non-UTF-8 messages as byte arrays.
        if isinstance(text, list):
            text = bytes(text).decode("utf-8", errors="replace")

        if isinstance(text, str):
            lines.append(text)

    return lines


def _final_json_object(lines: list[str]) -> dict[str, Any] | None:
    # Jobs print their result as the last line. Earlier JSON lines are
    # progress records and must not be mistaken for the result.
    if not lines:
        return None

    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None

    return value if isinstance(value, dict) else None


def _exit_status(value: str | None) -> int | str | None:
    if value is None:
        return None

    return int(value) if value.isdigit() else value


def _load_settings(path: Path) -> dict[str, str]:
    settings = {}

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return settings

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        key, separator, value = line.partition("=")

        if separator:
            settings[key.strip()] = value.strip()

    return settings

def _is_safe_webhook_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)

    if parsed.scheme == "https":
        return True

    return (
        parsed.scheme == "http"
        and parsed.hostname in ("127.0.0.1", "localhost", "::1")
    )

def _post_webhook(
    message: dict[str, Any],
    settings: dict[str, str],
) -> None:
    url = settings.get("KOUUN_WEBHOOK_URL")

    if not url:
        return
    
    if not _is_safe_webhook_url(url):
        _journal(
            "webhook skipped: use https or a loopback address",
            "warning",
        )
        return
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": f"kouun-notify/{MESSAGE_VERSION}",
    }
    token = settings.get("KOUUN_WEBHOOK_TOKEN")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=json.dumps(message, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=WEBHOOK_TIMEOUT_SECONDS,
        ) as response:
            response.read()
    except (urllib.error.URLError, OSError) as error:
        # The URL is not logged because it may contain a secret.
        _journal(
            f"webhook delivery failed: {error}",
            "warning",
        )


def _journal(text: str, priority: str) -> None:
    subprocess.run(
        [
            "systemd-cat",
            "-t",
            SYSLOG_IDENTIFIER,
            "-p",
            priority,
        ],
        input=text,
        text=True,
        check=True,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
