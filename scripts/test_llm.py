"""
Standalone smoke test for backend/llm.py. Requires FEATHERLESS_API_KEY to
be set (see .env). Not a pytest suite — run directly:

    python scripts/test_llm.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.llm import chat, chat_json, health_check

results = []


def _report(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    results.append(passed)


def test_health_check():
    try:
        result = health_check()
        assert result["ok"] is True, f"health_check returned ok=False: {result.get('error')}"
        _report(
            "health_check",
            True,
            f"model={result['model']} base_url={result['base_url']}",
        )
    except Exception as exc:
        _report("health_check", False, str(exc))


def test_chat_basic():
    try:
        messages = [{"role": "user", "content": "Reply with exactly one word: hello"}]
        response = chat(messages, max_tokens=10)
        assert isinstance(response, str) and response.strip() != "", "empty response"
        _report("chat_basic", True, response[:80])
    except Exception as exc:
        _report("chat_basic", False, str(exc))


def test_chat_with_system_prompt():
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a terse assistant. Reply in three words or less.",
            },
            {"role": "user", "content": "What is Python?"},
        ]
        response = chat(messages, max_tokens=50)
        assert isinstance(response, str) and response.strip() != "", "empty response"
        _report("chat_with_system_prompt", True, response)
    except Exception as exc:
        _report("chat_with_system_prompt", False, str(exc))


def test_chat_json_basic():
    try:
        messages = [
            {"role": "system", "content": "You extract structured data."},
            {
                "role": "user",
                "content": (
                    "Extract: 'Rekha is 18 years old and lives in Coimbatore'. "
                    "Return JSON with keys name, age, city."
                ),
            },
        ]
        result = chat_json(messages, schema_hint='{"name": str, "age": int, "city": str}')
        assert isinstance(result, dict), f"expected dict, got {type(result)}"
        assert result["name"].lower() == "rekha", f"unexpected name: {result.get('name')}"
        assert isinstance(result["age"], int) and result["age"] == 18, f"unexpected age: {result.get('age')}"
        _report("chat_json_basic", True, str(result))
    except Exception as exc:
        _report("chat_json_basic", False, str(exc))


def test_chat_json_error_surfacing():
    messages = [{"role": "user", "content": "Just say hi — do not return JSON."}]
    try:
        result = chat_json(messages, max_tokens=20)
        _report("chat_json_error_surfacing", True, f"model complied with JSON mode anyway: {result}")
    except ValueError as exc:
        _report("chat_json_error_surfacing", True, f"raised ValueError as documented: {exc}")
    except Exception as exc:
        _report("chat_json_error_surfacing", False, f"unexpected exception type: {exc!r}")


if __name__ == "__main__":
    test_health_check()
    test_chat_basic()
    test_chat_with_system_prompt()
    test_chat_json_basic()
    test_chat_json_error_surfacing()

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
