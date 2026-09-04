"""
backend/agents/filler.py

Real Filler agent logic (Rung 9). Pure function — no LangGraph imports.
For each SchemeThread at phase="docs_ready", builds the application form
payload from user_profile plus Validator's verified documents, asks
Featherless to infer any field UserProfile structurally can't supply
(bank_account_number — deliberately absent from UserProfile, see
_LLM_INFERRED_FIELDS below), then submits to the mock applications/submit
endpoint with one retry on failure.

Per-scheme work runs concurrently via a bounded ThreadPoolExecutor — same
rationale as backend.agents.validator (see its module docstring): true
LangGraph Send-based fan-out was assessed as more than the spec's
~60-minute budget, so the graph stays linear and concurrency happens here.

CONSTRAINT: never invents a SchemePhase Literal. "filing_failed" isn't a
real Literal in state.py, so a double submission failure reuses the
closest existing one, "docs_blocked" (this scheme can't proceed right
now) — flagged and confirmed before implementing rather than guessed.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.llm import chat_json
from backend.mocks.api import submit_application
from backend.mocks.models import ApplicationSubmitRequest
from backend.state import SevaState, UserProfile, make_reasoning_step

MAX_WORKERS = 4
INFERENCE_TEMPERATURE = 0.1

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "form_field_inference.txt"

# Straight profile -> form-field copy. Everything here already exists on
# UserProfile, so no inference is needed.
_PROFILE_FIELD_MAP = {
    "name": "name",
    "age": "age",
    "gender": "gender",
    "aadhaar_number": "aadhaar_number",
    "state": "state",
    "annual_income_inr": "annual_income_inr",
    "landholding_hectares": "landholding_hectares",
    "family_composition": "family_composition",
}

# Fields the application form wants that UserProfile has no field for at
# all — always routed through Featherless for a best-effort inference or
# an honest "cannot_infer" verdict. bank_account_number is deliberately
# absent from UserProfile (per the Rung 9 spec's own example) and, being
# something no document or profile field would legitimately reveal, is
# expected to come back "cannot_infer" in practice.
_LLM_INFERRED_FIELDS = ["bank_account_number"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    return text if text[-1] in ".!?" else text + "."


@lru_cache(maxsize=1)
def _load_inference_template() -> str:
    return _PROMPT_PATH.read_text()


def _build_base_payload(profile: UserProfile) -> dict:
    payload = {}
    for field_name, profile_key in _PROFILE_FIELD_MAP.items():
        value = profile.get(profile_key)
        if value not in (None, ""):
            payload[field_name] = value
    return payload


def _summarise_profile(profile: UserProfile) -> str:
    bits = []
    for label, key in (
        ("name", "name"), ("age", "age"), ("gender", "gender"),
        ("state", "state"), ("occupation", "occupation"),
        ("annual income", "annual_income_inr"),
    ):
        value = profile.get(key)
        if value:
            bits.append(f"{label}: {value}")
    return "; ".join(bits) if bits else "no structured profile fields available"


def _summarise_documents(documents: list) -> str:
    if not documents:
        return "no verified documents on file"
    lines = []
    for d in documents:
        note = f" ({d['notes']})" if d.get("notes") else ""
        lines.append(f"- {d['document_type']}: {d['status']}{note}")
    return "\n".join(lines)


def _infer_field(field_name: str, thread: dict, profile: UserProfile, documents: list, log) -> Optional[str]:
    prompt = _load_inference_template().format(
        scheme_name=thread["scheme_name"],
        field_name=field_name,
        profile_summary=_summarise_profile(profile),
        documents_summary=_summarise_documents(documents),
    )
    try:
        result = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a form-filling assistant for an Indian government scheme "
                        "application. Respond with strict JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=INFERENCE_TEMPERATURE,
            schema_hint='{"verdict": "inferred" | "cannot_infer", "value": str or null, "rationale": str}',
        )
        verdict = result["verdict"]
        rationale = str(result["rationale"])
        value = result.get("value")
    except Exception as exc:
        log("form_field_missing", f"Could not determine {field_name} ({exc}), so it's left blank on the application")
        return None

    if verdict == "inferred" and value:
        value = str(value)
        log("form_field_inferred", f"Inferred {field_name} as {value!r}: {rationale}")
        return value

    log("form_field_missing", f"{field_name} could not be inferred: {rationale}")
    return None


def _submit_with_retry(request: ApplicationSubmitRequest, log):
    last_exc = None
    for attempt in (1, 2):
        try:
            return submit_application(request)
        except Exception as exc:
            last_exc = exc
            if attempt == 1:
                log("submit_retry", f"The first submission attempt failed ({exc}); retrying once")

    log(
        "filing_failed",
        f"The submission failed twice ({last_exc}), so this scheme is blocked pending manual retry",
    )
    return None


def _fill_one_scheme(scheme_id: str, thread: dict, profile: UserProfile) -> tuple[dict, list]:
    local_log_steps: list[dict] = []

    def log(action: str, detail: str) -> None:
        local_log_steps.append(
            make_reasoning_step(
                agent="filler",
                action=action,
                detail=_ensure_sentence(detail),
                scheme_id=scheme_id,
            )
        )

    updated = dict(thread)
    try:
        documents = thread.get("documents") or []
        payload = _build_base_payload(profile)
        for field_name in _LLM_INFERRED_FIELDS:
            value = _infer_field(field_name, thread, profile, documents, log)
            if value is not None:
                payload[field_name] = value

        documents_attached = [d["document_type"] for d in documents if d.get("status") == "verified"]

        request = ApplicationSubmitRequest(
            aadhaar_number=profile.get("aadhaar_number") or "",
            scheme_id=scheme_id,
            documents_attached=documents_attached,
            applicant_profile=payload,
        )

        response = _submit_with_retry(request, log)

        if response is not None:
            updated["application_id"] = response.application_id
            updated["filed_at"] = response.submitted_at
            updated["phase"] = "filed"
            log("application_filed", f"Filed the application: {response.application_id}")
        else:
            # Reuses "docs_blocked" — state.py has no "filing_failed"
            # Literal; confirmed with the user before implementing.
            updated["phase"] = "docs_blocked"
            updated["error"] = "submission failed twice"
    except Exception as exc:
        updated["phase"] = "docs_blocked"
        updated["error"] = str(exc)
        log("filing_failed", f"Filling this application raised an unexpected error ({exc})")

    return updated, local_log_steps


def run_filler(state: SevaState) -> SevaState:
    """Runs Filler over every scheme_thread at phase="docs_ready" and
    returns a mutated copy of state.
    """
    profile: UserProfile = state["user_profile"]

    pending = [
        (scheme_id, thread)
        for scheme_id, thread in state["scheme_threads"].items()
        if thread["phase"] == "docs_ready"
    ]

    outcomes = []
    if pending:
        with ThreadPoolExecutor(max_workers=min(len(pending), MAX_WORKERS)) as pool:
            outcomes = list(
                pool.map(
                    lambda item: _fill_one_scheme(item[0], item[1], profile),
                    pending,
                )
            )

    new_scheme_threads = dict(state["scheme_threads"])
    new_reasoning_log = list(state["reasoning_log"])

    for (scheme_id, _thread), (updated, local_log_steps) in zip(pending, outcomes):
        new_scheme_threads[scheme_id] = updated
        new_reasoning_log.extend(local_log_steps)

    new_state = dict(state)
    new_state["scheme_threads"] = new_scheme_threads
    new_state["reasoning_log"] = new_reasoning_log
    new_state["current_phase"] = "execution"
    new_state["updated_at"] = _now_iso()
    return new_state  # type: ignore[return-value]
