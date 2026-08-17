"""CockroachDB Cloud ccloud CLI — Agent 可调用的只读运维工具。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from agent.config import ROOT


ALLOWED_PREFIXES = (
    "ccloud cluster list",
    "ccloud cluster describe",
    "ccloud cluster backup list",
    "ccloud organization list",
)


def _project_ccloud() -> Path | None:
    candidate = ROOT / ".tools" / "bin" / "ccloud"
    return candidate if candidate.is_file() and os.access(candidate, os.X_OK) else None


def _ccloud_bin() -> str | None:
    found = shutil.which("ccloud")
    if found:
        return found
    local = _project_ccloud()
    return str(local) if local else None


def _ccloud_available() -> bool:
    return _ccloud_bin() is not None


def run_ccloud(command: str) -> dict[str, Any]:
    cmd = command.strip()
    if not any(cmd.startswith(p) for p in ALLOWED_PREFIXES):
        return {
            "ok": False,
            "error": "command_not_allowed",
            "allowed": list(ALLOWED_PREFIXES),
        }
    binary = _ccloud_bin()
    if not binary:
        return {
            "ok": False,
            "error": "ccloud_not_installed",
            "hint": "运行 scripts/install_ccloud.sh 或 brew install cockroachdb/tap/ccloud",
        }
    if cmd.startswith("ccloud "):
        full_cmd = f"{binary} {cmd[len('ccloud '):]}"
    else:
        full_cmd = cmd
    if "--output json" not in full_cmd and " -o json" not in full_cmd:
        full_cmd += " --output json"
    env = os.environ.copy()
    tools_bin = str(ROOT / ".tools" / "bin")
    env["PATH"] = tools_bin + os.pathsep + env.get("PATH", "")
    try:
        proc = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or f"exit_{proc.returncode}"
            low = err.lower()
            if "not logged in" in low or "auth login" in low or "unauthorized" in low:
                return {
                    "ok": False,
                    "error": "ccloud_not_authenticated",
                    "hint": "运行: ccloud auth login",
                    "detail": err,
                }
            return {"ok": False, "error": err}
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
        "binary": _ccloud_bin(),
    }
