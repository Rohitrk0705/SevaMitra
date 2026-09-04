# SevaMithra LLM Wrapper

## Purpose
One module for every LLM call in the system. Agent nodes import from
backend.llm — never from openai directly.

## Backend
Local Ollama, model llama3.1:8b. Endpoint: http://127.0.0.1:11434/v1
(Ollama's OpenAI-compatible interface). No API keys. No cloud calls.

## Prerequisites
1. Ollama installed and running: `ollama serve` (or launched via the
   Ollama.app on macOS).
2. Model pulled: `ollama pull llama3.1:8b`
3. Verify: `ollama run llama3.1:8b "hello"` returns a response.

## Usage
Two functions cover 95% of use:

```python
from backend.llm import chat, chat_json

# Freeform text
response = chat([
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "What is RTI?"},
])

# Structured JSON
data = chat_json(
    [{"role": "user", "content": "Extract name and age from: ..."}],
    schema_hint='{"name": str, "age": int}',
)
```

## Configuration
All settings via environment variables (see .env.example):
- OLLAMA_BASE_URL (default: http://127.0.0.1:11434/v1)
- OLLAMA_MODEL (default: llama3.1:8b)
- LLM_TEMPERATURE (default: 0.2)
- LLM_MAX_TOKENS (default: 1024)
- LLM_TIMEOUT (default: 60)

## Smoke test
`python scripts/test_llm.py` — requires Ollama running.

## Error handling
chat() propagates openai exceptions unchanged; callers decide retry.
chat_json() raises ValueError with truncated raw output if JSON parsing
fails after salvage attempt.
