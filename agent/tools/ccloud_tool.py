"""CockroachDB Cloud ccloud CLI — Agent 可调用的只读运维工具。"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


ALLOWED_PREFIXES = (
    "ccloud cluster list",
    "ccloud cluster describe",
    "ccloud cluster backup list",
    "ccloud organization list",
)


def _ccloud_available() -> bool:
    return shutil.which("ccloud") is not None


def run_ccloud(command: str) -> dict[str, Any]:
    cmd = command.strip()
    if not any(cmd.startswith(p) for p in ALLOWED_PREFIXES):
        return {
            "ok": False,
            "error": "command_not_allowed",
            "allowed": list(ALLOWED_PREFIXES),
        }
    if not _ccloud_available():
        return {"ok": False, "error": "ccloud_not_installed"}
    full = cmd if "--output json" in cmd else cmd + " --output json"
    try:
        proc = subprocess.run(
            full,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": proc.stderr.strip() or f"exit_{proc.returncode}",
            }
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            data = {"raw": proc.stdout}
        return {"ok": True, "command": cmd, "data": data}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def cluster_health_summary() -> dict[str, Any]:
    result = run_ccloud("ccloud cluster list")
    if not result.get("ok"):
        return result
    clusters = result.get("data")
    if isinstance(clusters, dict):
        clusters = clusters.get("clusters") or clusters.get("items") or []
    count = len(clusters) if isinstance(clusters, list) else 0
    return {
        "ok": True,
        "cluster_count": count,
        "clusters": clusters,
    }
