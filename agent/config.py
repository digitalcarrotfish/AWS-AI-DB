from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


class Settings:
    storage_mode: str = _env("STORAGE_MODE", "json")
    database_url: str = _env("DATABASE_URL")
    bridge_data_dir: Path = Path(_env("BRIDGE_DATA_DIR", "data"))
    if not bridge_data_dir.is_absolute():
        bridge_data_dir = (ROOT / bridge_data_dir).resolve()

    llm_mode: str = _env("LLM_MODE", "retrieval")
    openai_api_base: str = _env("OPENAI_API_BASE", "https://api.moonshot.cn/v1").rstrip("/")
    openai_api_key: str = _env("OPENAI_API_KEY")
    openai_model: str = _env("OPENAI_MODEL", "kimi-k2.5")

    aws_region: str = _env("AWS_REGION", "us-east-1")
    aws_access_key_id: str = _env("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = _env("AWS_SECRET_ACCESS_KEY")
    bedrock_model_id: str = _env("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    bedrock_embed_model_id: str = _env("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")

    # Amazon S3（扫桥存证 / 研学报告）— Hackathon ≥1 AWS
    s3_bucket: str = _env("S3_BUCKET")
    s3_prefix: str = _env("S3_PREFIX", "qianhong")

    host: str = _env("HOST", "127.0.0.1")
    port: int = int(_env("PORT", "8787"))

    runtime_dir: Path = ROOT / "data" / "runtime"
    sessions_dir: Path = ROOT / "data" / "sessions"


settings = Settings()
settings.runtime_dir.mkdir(parents=True, exist_ok=True)
settings.sessions_dir.mkdir(parents=True, exist_ok=True)
