#!/usr/bin/env python3
"""Poke the radar when its 4-hourly scan went missing.

Runs from the public clip-radar-pulse repository every hour. Reads
``health.last_run`` out of the radar's committed state file and, if that is
older than STALE_SECONDS (3.5h by default), asks GitHub to start a scan via
``repository_dispatch``.

Why this exists: GitHub's scheduled workflows are best-effort. Runs can be
delayed by tens of minutes, dropped entirely, or never registered at all for a
brand-new private repo - and a scanner cannot notice its own silence. This repo
is the outside observer. It is public, so its Actions minutes are free.

Safety: the radar dedupes by campaign id, so an extra poke can never produce a
duplicate Telegram alert. At worst it costs one wasted scan.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

RADAR_REPO = os.environ.get("RADAR_REPO", "CJ0975/clip-radar")
PAT = os.environ.get("RADAR_PAT", "").strip()
FORCE = os.environ.get("FORCE", "").strip().lower() == "true"
STALE_SECONDS = int(os.environ.get("STALE_SECONDS", "12600"))  # 3.5 hours
TG_TOKEN = os.environ.get("TG_TOKEN", "").strip()
TG_CHAT = os.environ.get("TG_CHAT", "").strip()
API = "https://api.github.com"


def api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {PAT}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "clip-radar-pulse",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": exc.read().decode(errors="replace")[:200]}


def telegram(text: str) -> None:
    if not TG_TOKEN or not TG_CHAT:
        print("(no telegram credentials - cannot send the warning)")
        return
    payload = json.dumps({"chat_id": TG_CHAT, "text": text}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=20).read()
        print("telegram warning sent")
    except Exception as exc:  # noqa: BLE001 - never mask the real error
        print(f"telegram failed too: {exc}")


def read_health() -> tuple[str | None, str | None]:
    status, data = api("GET", f"/repos/{RADAR_REPO}/contents/data/state.json?ref=main")
    if status != 200:
        raise RuntimeError(f"state.json fetch returned HTTP {status}")
    payload = json.loads(base64.b64decode(data["content"]))
    health = payload.get("health") or {}
    return health.get("last_run"), health.get("last_event")


def main() -> int:
    if not PAT:
        print("RADAR_PAT is not set")
        return 1

    try:
        last_run, last_event = read_health()
    except Exception as exc:  # noqa: BLE001
        print(f"cannot read the radar's state file: {exc}")
        telegram(
            "⚠️ Clip Radar pulse: cannot read the radar's state file, so the "
            "backstop cannot help. Its GitHub token has probably expired or been "
            "revoked - the 4-hourly scans may have stopped."
        )
        return 1

    age: int | None = None
    if last_run:
        stamp = datetime.fromisoformat(last_run)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        age = int((datetime.now(timezone.utc) - stamp).total_seconds())

    print(f"last scan: {last_run or 'never'} ({age if age is not None else '?'}s ago)")
    print(f"triggered by: {last_event or 'unknown'}")

    if not FORCE and age is not None and age < STALE_SECONDS:
        print(f"fresh (< {STALE_SECONDS}s): nothing to do")
        return 0

    print("overdue - poking the radar")
    status, _ = api(
        "POST",
        f"/repos/{RADAR_REPO}/dispatches",
        {"event_type": "pulse", "client_payload": {"why": f"no scan for {age}s"}},
    )
    print(f"repository_dispatch -> HTTP {status}")
    if status != 204:
        telegram(
            f"⚠️ Clip Radar pulse could not start a scan (HTTP {status}). "
            "The 4-hourly schedule is not running and the backstop is blocked."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
