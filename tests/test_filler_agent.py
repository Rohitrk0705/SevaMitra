"""
tests/test_filler_agent.py

Unit tests for backend.agents.filler.run_filler. submit_application is
monkeypatched for the retry-behavior tests (need control over exactly
when it fails); chat_json (Featherless) is monkeypatched everywhere,
matching the established pattern.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.agents.filler as filler_mod
from backend.mocks.fixtures import RAJESH_AADHAAR
from backend.state import create_initial_state, make_scheme_thread


def _docs_ready_thread(scheme_id="TN-AGRI-002"):
    thread = make_scheme_thread(scheme_id, "Farmer Input Subsidy", 0.85)
    thread["phase"] = "docs_ready"
    thread["documents"] = [
        {
            "document_type": "aadhaar_card",
            "status": "verified",
            "source": "digilocker",
            "last_checked_at": "2026-09-04T00:00:00+00:00",
            "notes": "",
        },
        {
            "document_type": "bank_passbook",
            "status": "verified",
            "source": "digilocker",
            "last_checked_at": "2026-09-04T00:00:00+00:00",
            "notes": "",
        },
    ]
    return thread


def _state_with_thread(thread):
    state = create_initial_state(raw_input="test")
    state["user_profile"]["aadhaar_number"] = RAJESH_AADHAAR
    state["user_profile"]["name"] = "Rajesh Kumar"
    state["user_profile"]["age"] = 45
    state["user_profile"]["state"] = "Tamil Nadu"
    state["scheme_threads"] = {thread["scheme_id"]: thread}
    return state


def _cannot_infer_chat_json(messages, **kwargs):
    return {"verdict": "cannot_infer", "value": None, "rationale": "A bank account number cannot be inferred from any document on file"}


def test_filled_and_submitted_advances_phase(monkeypatch):
    monkeypatch.setattr(filler_mod, "chat_json", _cannot_infer_chat_json)

    state = _state_with_thread(_docs_ready_thread())
    result = filler_mod.run_filler(state)
    updated = result["scheme_threads"]["TN-AGRI-002"]

    assert updated["phase"] == "filed"
    assert updated["application_id"]
    assert updated["filed_at"]

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "application_filed" in actions
    assert "form_field_missing" in actions


def test_missing_optional_field_llm_infers(monkeypatch):
    def fake_chat_json(messages, **kwargs):
        return {"verdict": "inferred", "value": "1234567890", "rationale": "The verified bank passbook implies an active savings account"}

    monkeypatch.setattr(filler_mod, "chat_json", fake_chat_json)

    state = _state_with_thread(_docs_ready_thread())
    result = filler_mod.run_filler(state)
    updated = result["scheme_threads"]["TN-AGRI-002"]

    assert updated["phase"] == "filed"

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "form_field_inferred" in actions
    inferred_step = next(s for s in result["reasoning_log"] if s["action"] == "form_field_inferred")
    assert "1234567890" in inferred_step["detail"]


def test_submit_retry_on_first_failure(monkeypatch):
    monkeypatch.setattr(filler_mod, "chat_json", _cannot_infer_chat_json)

    calls = {"n": 0}

    def flaky_submit(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("mock submit endpoint temporarily unavailable")
        return SimpleNamespace(application_id="APP-TEST-RETRY-1", submitted_at="2026-09-04T00:00:00+00:00")

    monkeypatch.setattr(filler_mod, "submit_application", flaky_submit)

    state = _state_with_thread(_docs_ready_thread())
    result = filler_mod.run_filler(state)
    updated = result["scheme_threads"]["TN-AGRI-002"]

    assert calls["n"] == 2
    assert updated["phase"] == "filed"
    assert updated["application_id"] == "APP-TEST-RETRY-1"

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "submit_retry" in actions
    assert "application_filed" in actions


def test_submit_double_failure_marks_failed(monkeypatch):
    monkeypatch.setattr(filler_mod, "chat_json", _cannot_infer_chat_json)

    def always_fails(request):
        raise RuntimeError("mock submit endpoint down")

    monkeypatch.setattr(filler_mod, "submit_application", always_fails)

    state = _state_with_thread(_docs_ready_thread())
    result = filler_mod.run_filler(state)
    updated = result["scheme_threads"]["TN-AGRI-002"]

    # "filing_failed" isn't a real SchemePhase Literal (confirmed with the
    # user before implementing) — reuses "docs_blocked", the closest
    # existing member.
    assert updated["phase"] == "docs_blocked"
    assert updated["application_id"] is None

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "filing_failed" in actions
