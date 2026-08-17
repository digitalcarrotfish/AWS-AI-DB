from __future__ import annotations

import json
import re
from typing import Any

import httpx

from agent.config import settings
from agent.knowledge import format_bridge_brief


def build_system_prompt(
    bridges_context: str,
    memory_summary: str | None,
    focus_bridge: dict[str, Any] | None,
) -> str:
    parts = [
        "你是「千古飞虹 · 飞虹智忆」古桥文化 Agent，基于权威图鉴资料作答，勿编造不存在的桥梁。",
        "回答应准确、有文采，可引用诗词与工程要点。",
    ]
    if memory_summary:
        parts.append(f"\n【用户长期记忆】\n{memory_summary}")
    if focus_bridge:
        culture = focus_bridge.get("_culture")
        parts.append("\n【当前关注桥梁】\n" + format_bridge_brief(focus_bridge, culture))
    parts.append("\n【检索到的相关资料】\n" + bridges_context)
    return "\n".join(parts)


def chat_with_llm(
    system: str,
    history: list[dict[str, str]],
    user_message: str,
) -> tuple[str, str]:
    mode = settings.llm_mode
    if mode == "bedrock":
        try:
            return _bedrock_chat(system, history, user_message), "bedrock"
        except Exception as exc:
            if mode == "bedrock":
                raise exc
    if mode == "openai" and settings.openai_api_key:
        return _openai_chat(system, history, user_message), "openai"
    raise RuntimeError("未配置 LLM（设置 LLM_MODE=openai 并填写 OPENAI_API_KEY，或开通 Bedrock）")


def _openai_chat(
    system: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    messages = [{"role": "system", "content": system}]
    for m in history[-12:]:
        if m["role"] in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_message})
    url = settings.openai_api_base + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 1200,
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return text.strip()


def _bedrock_client():
    import boto3

    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("bedrock-runtime", **kwargs)


def _bedrock_chat(
    system: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    client = _bedrock_client()
    converse_messages = []
    anthropic_messages = []
    for m in history[-12:]:
        if m["role"] in ("user", "assistant"):
            converse_messages.append({
                "role": m["role"],
                "content": [{"text": m["content"]}],
            })
            anthropic_messages.append({"role": m["role"], "content": m["content"]})
    converse_messages.append({"role": "user", "content": [{"text": user_message}]})
    anthropic_messages.append({"role": "user", "content": user_message})

    # 优先 Converse API（Claude 3/3.5 更稳）
    try:
        resp = client.converse(
            modelId=settings.bedrock_model_id,
            system=[{"text": system}],
            messages=converse_messages,
            inferenceConfig={"maxTokens": 1200, "temperature": 0.6},
        )
        parts = resp.get("output", {}).get("message", {}).get("content") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if text.strip():
            return text.strip()
    except Exception:
        pass

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1200,
        "system": system,
        "messages": anthropic_messages,
    }
    resp = client.invoke_model(
        modelId=settings.bedrock_model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(resp["body"].read())
    blocks = payload.get("content") or []
    return "".join(b.get("text", "") for b in blocks).strip()
