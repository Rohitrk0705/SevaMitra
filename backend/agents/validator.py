"""
backend/agents/validator.py

Real Validator agent logic (Rung 9). Pure function — no LangGraph imports.
For each SchemeThread at phase="discovered", fetches the citizen's
DigiLocker documents once and checks every scheme.required_documents entry
against them: present -> verified, missing-with-fallback -> recovered via
an acceptable alternative, missing-with-no-fallback -> blocks the scheme,
conflicting (DigiLocker returned multiple differing records) -> a single
Featherless tie-break call resolves which record is admissible.

Per-scheme work runs concurrently via a bounded ThreadPoolExecutor (see
module docstring note below on why this isn't LangGraph-level Send fan-out).

DEVIATIONS (flagged during planning):
  - True LangGraph Send-based per-scheme graph parallelism was assessed as
    a real architecture change (new reducer for scheme_threads, retooling
    builder.py's linear StateGraph, risk to the checkpointer/
    interrupt_before tests) — well past the spec's ~60-minute budget. Per
    the documented fallback, the graph stays linear; concurrency happens
    here instead, via ThreadPoolExecutor over per-scheme DigiLocker/
    Featherless I/O. Reasoning steps still carry scheme_id (already a
    ReasoningStep field) so the frontend can lane them without a text
    prefix.
  - DigiLocker is called via backend.mocks.api's route functions directly
    (same in-process pattern backend.agents.discovery already uses for
    backend.ingestion.retrieve.query_schemes) rather than over HTTP.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.llm import chat_json
from backend.mocks.api import fetch_digilocker_documents
from backend.state import (
    DocumentStatus,
    SevaState,
    UserProfile,
    make_reasoning_step,
)

MAX_WORKERS = 4
TIEBREAK_TEMPERATURE = 0.1

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "doc_conflict_resolution.txt"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    return text if text[-1] in ".!?" else text + "."


@lru_cache(maxsize=1)
def _load_conflict_template() -> str:
    return _PROMPT_PATH.read_text()


def _fetch_documents_by_type(aadhaar_number: Optional[str]) -> dict[str, list[dict]]:
    """Returns {document_type: [document dict, ...]}. Empty dict on any
    failure (no aadhaar_number, unknown aadhaar, endpoint error) — every
    required document is then correctly treated as missing rather than
    crashing the whole Validator run.
    """
    if not aadhaar_number:
        return {}
    try:
        response = fetch_digilocker_documents(aadhaar_number)
    except Exception:
        return {}

    by_type: dict[str, list[dict]] = {}
    for doc in response.documents:
        by_type.setdefault(doc.document_type, []).append(doc.model_dump())
    return by_type


def _valid_entries(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("status") == "valid"]


def _doc_status(document_type: str, status: str, source_doc: Optional[dict], notes: str = "") -> DocumentStatus:
    return DocumentStatus(
        document_type=document_type,
        status=status,
        source="digilocker" if source_doc else "none",
        last_checked_at=_now_iso(),
        notes=notes,
    )


def _summarise_records(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        meta = ", ".join(f"{k}={v}" for k, v in (e.get("metadata") or {}).items())
        lines.append(
            f"- document_id={e['document_id']}, issued_at={e['issued_at']}, "
            f"issued_by={e['issued_by']}" + (f", {meta}" if meta else "")
        )
    return "\n".join(lines)


def _resolve_conflict_with_llm(scheme_name: str, document_type: str, entries: list[dict], log) -> Optional[dict]:
    prompt = _load_conflict_template().format(
        scheme_name=scheme_name,
        document_type=document_type,
        records_summary=_summarise_records(entries),
    )
    try:
        result = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a document conflict resolver for an Indian government "
                        "scheme discovery assistant. Respond with strict JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=TIEBREAK_TEMPERATURE,
            schema_hint='{"admissible_record": str, "rationale": str, "confidence": float}',
        )
        chosen_id = result["admissible_record"]
        rationale = str(result["rationale"])
    except Exception as exc:
        log(
            "doc_conflict_unresolvable",
            f"Could not resolve the conflicting {document_type} records ({exc}), so this "
            "scheme is blocked pending manual review",
        )
        return None

    chosen = next((e for e in entries if e.get("document_id") == chosen_id), None)
    if chosen is None:
        log(
            "doc_conflict_unresolvable",
            f"The tie-break named a {document_type} record that doesn't match any record on "
            "file, so this scheme is blocked pending manual review",
        )
        return None

    log("doc_conflict_resolved", f"Resolved the conflicting {document_type} records: {rationale}")
    return chosen


def _validate_one_scheme(scheme_id: str, thread: dict, digilocker_docs_by_type: dict) -> tuple[list[DocumentStatus], list[str], list[dict]]:
    """Returns (document_statuses, blocked_on, new_reasoning_steps)."""
    local_log_steps: list[dict] = []

    def log(action: str, detail: str) -> None:
        local_log_steps.append(
            make_reasoning_step(
                agent="validator",
                action=action,
                detail=_ensure_sentence(detail),
                scheme_id=scheme_id,
            )
        )

    fallback_map = {
        f["primary_doc"]: f["acceptable_alternatives"]
        for f in thread.get("fallback_documents") or []
    }

    document_statuses: list[DocumentStatus] = []
    blocked_on: list[str] = []

    for doc_type in thread.get("required_documents") or []:
        entries = _valid_entries(digilocker_docs_by_type.get(doc_type, []))

        if len(entries) == 1:
            log("doc_verified", f"{doc_type.replace('_', ' ')} is present and unambiguous")
            document_statuses.append(_doc_status(doc_type, "verified", entries[0]))
            continue

        if len(entries) > 1:
            distinct = {json.dumps(e.get("metadata") or {}, sort_keys=True) for e in entries}
            if len(distinct) == 1:
                log("doc_verified", f"{doc_type.replace('_', ' ')} is present and unambiguous")
                document_statuses.append(_doc_status(doc_type, "verified", entries[0]))
                continue

            resolved = _resolve_conflict_with_llm(thread["scheme_name"], doc_type, entries, log)
            if resolved is None:
                blocked_on.append(doc_type)
                document_statuses.append(
                    _doc_status(doc_type, "mismatch", entries[0], notes="conflicting records, unresolved")
                )
            else:
                document_statuses.append(
                    _doc_status(doc_type, "verified", resolved, notes="resolved from conflicting records")
                )
            continue

        # entries is empty -> missing. Check for an acceptable fallback.
        alternatives = fallback_map.get(doc_type) or []
        recovered_via = None
        recovered_doc = None
        for alt in alternatives:
            alt_entries = _valid_entries(digilocker_docs_by_type.get(alt, []))
            if alt_entries:
                recovered_via = alt
                recovered_doc = alt_entries[0]
                break

        if recovered_doc is not None:
            log(
                "doc_recovered_via_fallback",
                f"{doc_type.replace('_', ' ')} was missing, but "
                f"{recovered_via.replace('_', ' ')} was accepted as an acceptable alternative",
            )
            document_statuses.append(
                _doc_status(doc_type, "verified", recovered_doc, notes=f"recovered via fallback: {recovered_via}")
            )
        else:
            log(
                "doc_missing_no_fallback",
                f"{doc_type.replace('_', ' ')} is missing and no acceptable fallback document is on file",
            )
            blocked_on.append(doc_type)
            document_statuses.append(_doc_status(doc_type, "missing", None))

    return document_statuses, blocked_on, local_log_steps


def run_validator(state: SevaState) -> SevaState:
    """Runs Validator over every scheme_thread at phase="discovered" and
    returns a mutated copy of state. Never calls the Filler or the submit
    endpoint — that's the Filler agent's job.
    """
    profile: UserProfile = state["user_profile"]
    aadhaar_number = profile.get("aadhaar_number")
    digilocker_docs_by_type = _fetch_documents_by_type(aadhaar_number)

    pending = [
        (scheme_id, thread)
        for scheme_id, thread in state["scheme_threads"].items()
        if thread["phase"] == "discovered"
    ]

    outcomes = []
    if pending:
        with ThreadPoolExecutor(max_workers=min(len(pending), MAX_WORKERS)) as pool:
            outcomes = list(
                pool.map(
                    lambda item: _validate_one_scheme(item[0], item[1], digilocker_docs_by_type),
                    pending,
                )
            )

    new_scheme_threads = dict(state["scheme_threads"])
    new_reasoning_log = list(state["reasoning_log"])

    for (scheme_id, thread), (document_statuses, blocked_on, local_log_steps) in zip(pending, outcomes):
        updated = dict(thread)
        updated["documents"] = document_statuses
        updated["blocked_on"] = blocked_on
        updated["phase"] = "docs_blocked" if blocked_on else "docs_ready"
        new_scheme_threads[scheme_id] = updated
        new_reasoning_log.extend(local_log_steps)

    new_state = dict(state)
    new_state["scheme_threads"] = new_scheme_threads
    new_state["reasoning_log"] = new_reasoning_log
    new_state["current_phase"] = "verification"
    new_state["updated_at"] = _now_iso()
    return new_state  # type: ignore[return-value]
