import ast
import json
import re
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


THINK_RE = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)


def split_thinking(content: str) -> tuple[str, str]:
    thoughts = [match.strip() for match in THINK_RE.findall(content) if match.strip()]
    visible = THINK_RE.sub("", content).strip()
    return "\n\n".join(thoughts), visible


def parse_structured_candidate(candidate: str):
    value = candidate.strip()
    for _ in range(3):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError, TypeError):
                return None
        if isinstance(parsed, str):
            value = parsed.strip()
            continue
        return parsed
    return None


def extract_json_object(content: str) -> dict | None:
    _, text = split_thinking(content)
    text = text.strip()
    candidates = [text]
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            candidates.append("\n".join(lines[1:-1]).strip())
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        parsed = parse_structured_candidate(candidate)
        if isinstance(parsed, dict):
            return parsed
    return None


def list_value(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalize_result(content: str) -> dict:
    thinking, visible_content = split_thinking(content)
    fallback = {
        "assistant_message": visible_content.strip() or "我已经收到你的想法，可以继续补充目标用户、使用场景或核心功能。",
        "thinking": thinking,
        "ready": False,
        "prd": [],
        "flow": [],
        "tasks": [],
    }
    parsed = extract_json_object(content)
    if parsed is None:
        return fallback
    if not isinstance(parsed, dict):
        return fallback
    return {
        "assistant_message": str(parsed.get("assistant_message") or "我会继续帮你收敛这个产品想法。"),
        "thinking": thinking or str(parsed.get("thinking") or parsed.get("thought") or "").strip(),
        "ready": bool(parsed.get("ready")),
        "prd": list_value(parsed.get("prd")),
        "flow": list_value(parsed.get("flow")),
        "tasks": list_value(parsed.get("tasks")),
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
