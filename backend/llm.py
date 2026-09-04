"""
backend/llm.py

The single LLM wrapper for the entire SevaMithra codebase. Every agent node
(Discovery, Validator, Filler, Monitor, Escalation) calls chat() or
chat_json() from here — nothing imports openai or requests directly.

Backend: Featherless.ai, served at its OpenAI-compatible /v1 endpoint.
Requires FEATHERLESS_API_KEY. This is the only LLM provider in the
codebase — no local/Ollama fallback.

Rung 9: when USE_CACHED_LLM=true, both chat() and chat_json() look up
their response in backend/cache/<hash>.json before making a live call
(the spec's own pseudocode only showed this wired into chat(), but
Validator/Filler's LLM calls go through chat_json(), so the identical
pattern is applied there too — same rationale: demo-reliable replay).
On a cache miss, the live call still happens and its result is written to
that path, so cached responses get recorded simply by running a flow once
with the env var set. See backend/cache/README.md.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import openai

FEATHERLESS_BASE_URL = os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
FEATHERLESS_MODEL = os.getenv("FEATHERLESS_MODEL", "Qwen/Qwen2.5-7B-Instruct")
FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY")

DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT", "60"))

CACHE_DIR = Path(__file__).resolve().parent / "cache"

logger = logging.getLogger(__name__)

_client: Optional["openai.OpenAI"] = None


def _cache_enabled() -> bool:
    return os.getenv("USE_CACHED_LLM", "").lower() == "true"


def _cache_path(kind: str, messages: list) -> Path:
    # `kind` keeps chat()'s plain-string cache separate from chat_json()'s
    # parsed-object cache even if two call sites happen to send identical
    # messages.
    payload = json.dumps({"kind": kind, "messages": messages}, sort_keys=True)
    cache_key = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{cache_key}.json"


def _cache_read(cache_path: Path) -> tuple[bool, Any]:
    if cache_path.exists():
        return True, json.loads(cache_path.read_text())
    return False, None


def _cache_write(cache_path: Path, value: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(value))


def get_client() -> "openai.OpenAI":
    """Returns a cached openai.OpenAI client pointed at Featherless's /v1 endpoint."""
    global _client
    if _client is None:
        _client = openai.OpenAI(
            base_url=FEATHERLESS_BASE_URL,
            api_key=FEATHERLESS_API_KEY,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    return _client


def get_active_model() -> str:
    """Returns the active model name. Call this rather than hardcoding."""
    return FEATHERLESS_MODEL


def chat(
    messages: list,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: Optional[str] = None,
    stop: Optional[list] = None,
) -> str:
    """Blocking chat completion. Returns the assistant message content."""
    cache_path = None
    if _cache_enabled():
        cache_path = _cache_path("chat", messages)
        hit, cached = _cache_read(cache_path)
        if hit:
            return cached

    active_model = model or get_active_model()
    prompt_chars = sum(len(m.get("content", "")) for m in messages)

    # Featherless's endpoint 422s on an explicit stop=null (unlike OpenAI's,
    # which tolerates it) — only send the key when there's a real value.
    extra_kwargs = {"stop": stop} if stop is not None else {}

    start = time.monotonic()
    response = get_client().chat.completions.create(
        model=active_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **extra_kwargs,
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    content = response.choices[0].message.content or ""
    logger.info(
        "llm.chat model=%s msgs=%d prompt_chars=%d resp_chars=%d duration_ms=%d",
        active_model,
        len(messages),
        prompt_chars,
        len(content),
        duration_ms,
    )

    if cache_path is not None:
        _cache_write(cache_path, content)
    return content


def _extract_json_block(text: str) -> str:
    """Balanced-brace scan for the first {...} or [...] block in text."""
    open_chars = "{["
    close_chars = "}]"
    start_idx = None
    for i, ch in enumerate(text):
        if ch in open_chars:
            start_idx = i
            break
    if start_idx is None:
        raise ValueError("No JSON object or array found in content")

    stack = [text[start_idx]]
    for i in range(start_idx + 1, len(text)):
        ch = text[i]
        if ch in open_chars:
            stack.append(ch)
        elif ch in close_chars:
            stack.pop()
            if not stack:
                return text[start_idx : i + 1]
    raise ValueError("Unbalanced braces — no complete JSON block found")


def chat_json(
    messages: list,
    *,
    temperature: float = 0.1,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: Optional[str] = None,
    schema_hint: Optional[str] = None,
) -> Any:
    """Chat completion that returns parsed JSON, with a salvage fallback."""
    messages = [dict(m) for m in messages]

    if schema_hint:
        hint_line = f"Respond with a JSON object matching this shape: {schema_hint}"
        for m in messages:
            if m.get("role") == "system":
                m["content"] = f"{hint_line}\n\n{m['content']}"
                break
        else:
            messages.insert(0, {"role": "system", "content": hint_line})

    cache_path = None
    if _cache_enabled():
        cache_path = _cache_path("chat_json", messages)
        hit, cached = _cache_read(cache_path)
        if hit:
            return cached

    active_model = model or get_active_model()
    prompt_chars = sum(len(m.get("content", "")) for m in messages)

    start = time.monotonic()
    response = get_client().chat.completions.create(
        model=active_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    content = response.choices[0].message.content or ""
    logger.info(
        "llm.chat_json model=%s msgs=%d prompt_chars=%d resp_chars=%d duration_ms=%d",
        active_model,
        len(messages),
        prompt_chars,
        len(content),
        duration_ms,
    )

    result = None
    parsed = False
    try:
        result = json.loads(content)
        parsed = True
    except json.JSONDecodeError:
        pass

    if not parsed:
        try:
            salvaged = _extract_json_block(content)
            result = json.loads(salvaged)
            parsed = True
        except (ValueError, json.JSONDecodeError):
            pass

    if not parsed:
        truncated = content[:500]
        raise ValueError(f"chat_json: failed to parse JSON from model output: {truncated!r}")

    if cache_path is not None:
        _cache_write(cache_path, result)
    return result


def health_check() -> dict:
    """Trivial chat() call to verify the Ollama backend is reachable."""
    result = {
        "ok": False,
        "model": get_active_model(),
        "base_url": FEATHERLESS_BASE_URL,
        "error": None,
    }
    try:
        chat(
            [{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=10,
        )
        result["ok"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result
