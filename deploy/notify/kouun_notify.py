"""Notify kouun_db job events from systemd units.

started <job>: called from ExecStartPre of each job unit.
result <job>:  called from kouun-notify@<job>.service via OnSuccess=/OnFailure=.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
SYSLOG_IDENTIFIER = "kouun-notify"
LOG_TAIL_LINES = 20

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
        message = _base_message("started", job, unit)
    else:
        message = _result_message(job, unit)

    _emit(message)
    return 0


def _base_message(
    event: str,
    job: str,
    unit: str,
) -> dict[str, Any]:
    return {
        "event": event,
        "job": job,
        "unit": unit,
        "host": socket.gethostname(),
        "at": datetime.now(JST).isoformat(timespec="seconds"),
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
    )
    message.update(
        {
            "invocation_id": invocation_id,
            "service_result": service_result,
            "exit_status": _exit_status(
                state.get("ExecMainStatus")
            ),
            "summary": _last_json_object(lines),
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


def _last_json_object(lines: list[str]) -> dict[str, Any] | None:
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            return value

    return None


def _exit_status(value: str | None) -> int | str | None:
    # A killed process reports a signal name such as "KILL".
    if value is None:
        return None

    return int(value) if value.isdigit() else value


def _emit(message: dict[str, Any]) -> None:
    priority = "err" if message["event"] == "failed" else "info"

    subprocess.run(
        [
            "systemd-cat",
            "-t",
            SYSLOG_IDENTIFIER,
            "-p",
            priority,
        ],
        input=json.dumps(message, ensure_ascii=False),
        text=True,
        check=True,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
