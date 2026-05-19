import json
from urllib.parse import urljoin

import httpx

from .config import get_settings


SYSTEM_PROMPT = """你是 Think Land 的产品方案助手。
你要通过多轮对话帮助用户把模糊想法变成清晰产品目标。
如果信息不足，请用 assistant_message 提出 1 到 3 个关键追问，ready 返回 false。
如果信息足够，请用 assistant_message 简短说明已经整理好方案，ready 返回 true，并生成 PRD、流程、任务。
只返回 JSON，不要返回 Markdown。
JSON 格式必须是：
{
  "assistant_message": "给用户的下一句话",
  "ready": true,
  "prd": ["4 到 6 条 PRD 要点"],
  "flow": ["4 到 6 个业务流程节点"],
  "tasks": ["4 到 6 个下一步任务"]
}
内容使用简体中文，具体、可执行。"""


def normalize_result(content: str) -> dict:
    fallback = {
        "assistant_message": content.strip() or "我已经收到你的想法，可以继续补充目标用户、使用场景或核心功能。",
        "ready": False,
        "prd": [],
        "flow": [],
        "tasks": [],
    }
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return fallback
    if not isinstance(parsed, dict):
        return fallback
    return {
        "assistant_message": str(parsed.get("assistant_message") or "我会继续帮你收敛这个产品想法。"),
        "ready": bool(parsed.get("ready")),
        "prd": list(parsed.get("prd") or []),
        "flow": list(parsed.get("flow") or []),
        "tasks": list(parsed.get("tasks") or []),
    }


async def generate_product_plan(base_url: str, api_key: str, model: str, messages: list[dict], max_tokens: int) -> dict:
    endpoint = urljoin(base_url.rstrip("/") + "/", "chat/completions")
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "temperature": 0.4,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    timeout = get_settings().openai_compat_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"AI 接口调用失败：HTTP {response.status_code} {response.text[:300]}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    return {
        "result": normalize_result(content),
        "usage": {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        },
    }

