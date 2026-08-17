"""Amazon S3 — 扫桥存证与研学报告（Hackathon ≥1 AWS 服务）。"""
from __future__ import annotations

import json
import mimetypes
import uuid
from datetime import datetime, timezone
from typing import Any

from agent.config import settings


def s3_enabled() -> bool:
    return bool(settings.s3_bucket)


def _client():
    import boto3

    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def status() -> dict[str, Any]:
    if not s3_enabled():
        return {
            "ok": False,
            "enabled": False,
            "hint": "设置 S3_BUCKET 后启用（见 docs/AWS.md）",
        }
    try:
        client = _client()
        client.head_bucket(Bucket=settings.s3_bucket)
        return {
            "ok": True,
            "enabled": True,
            "bucket": settings.s3_bucket,
            "region": settings.aws_region,
            "prefix": settings.s3_prefix,
        }
    except Exception as exc:
        return {
            "ok": False,
            "enabled": True,
            "bucket": settings.s3_bucket,
            "error": str(exc),
        }


def put_bytes(
    *,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not s3_enabled():
        raise RuntimeError("S3_BUCKET 未配置")
    client = _client()
    full_key = f"{settings.s3_prefix.rstrip('/')}/{key.lstrip('/')}"
    extra: dict[str, Any] = {"ContentType": content_type}
    if metadata:
        extra["Metadata"] = {k: str(v)[:256] for k, v in metadata.items()}
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=full_key,
        Body=data,
        **extra,
    )
    uri = f"s3://{settings.s3_bucket}/{full_key}"
    return {
        "ok": True,
        "bucket": settings.s3_bucket,
        "key": full_key,
        "uri": uri,
        "https": f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{full_key}",
    }


def put_json(key: str, payload: dict[str, Any], metadata: dict[str, str] | None = None) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return put_bytes(
        key=key,
        data=body,
        content_type="application/json; charset=utf-8",
        metadata=metadata,
    )


def upload_scan_image(
    *,
    session_id: str | None,
    bridge_name: str | None,
    filename: str | None,
    raw: bytes,
) -> dict[str, Any] | None:
    if not s3_enabled() or not raw:
        return None
    ext = "jpg"
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()[:8]
    ctype = mimetypes.guess_type(filename or f"x.{ext}")[0] or "image/jpeg"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_bridge = (bridge_name or "unknown").replace("/", "_")[:40]
    sid = (session_id or "anon")[:36]
    key = f"scans/{sid}/{stamp}_{safe_bridge}_{uuid.uuid4().hex[:8]}.{ext}"
    return put_bytes(
        key=key,
        data=raw,
        content_type=ctype,
        metadata={
            "session_id": sid,
            "bridge": safe_bridge,
            "source": "camera_scan",
        },
    )


def export_study_report(
    *,
    session_id: str,
    dossier: dict[str, Any],
    study_path: dict[str, Any] | None,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    if not s3_enabled():
        raise RuntimeError("S3_BUCKET 未配置")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "exported_at": stamp,
        "session_id": session_id,
        "dossier": dossier,
        "study_path": study_path,
        "events": events[-50:],
        "project": "飞虹智忆 qianhong-agent",
        "hackathon": "https://cockroachdb-ai.devpost.com/",
    }
    key = f"reports/{session_id}/{stamp}_dossier.json"
    return put_json(
        key,
        payload,
        metadata={"session_id": session_id[:36], "kind": "study_report"},
    )
