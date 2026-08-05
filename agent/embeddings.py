from __future__ import annotations

from agent.config import settings
from agent.knowledge import hash_embed


def embed_text(text: str) -> list[float]:
    mode = settings.llm_mode
    if mode == "bedrock":
        try:
            return _bedrock_embed(text)
        except Exception:
            pass
    return hash_embed(text)


def _bedrock_embed(text: str) -> list[float]:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    body = {"inputText": text[:8000]}
    if "v2" in settings.bedrock_embed_model_id:
        body["dimensions"] = 1024
        body["normalize"] = True
    resp = client.invoke_model(
        modelId=settings.bedrock_embed_model_id,
        body=__import__("json").dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = __import__("json").loads(resp["body"].read())
    return payload.get("embedding") or payload.get("embeddings", [[]])[0]
