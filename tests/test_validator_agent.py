"""
tests/test_validator_agent.py

Unit tests for backend.agents.validator.run_validator. DigiLocker calls go
through the real backend.mocks.api / backend.mocks.fixtures data (that's
the whole point of Rung 9's persona fixtures — Rekha clean, Rajesh
conflicting land records + missing-with-fallback land patta, both real
demo scenarios). Only chat_json (Featherless) is monkeypatched, matching
the pattern established in tests/test_discovery_agent.py: mock the
expensive/nondeterministic external dependency, not the deterministic
mock APIs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.agents.validator as validator_mod
from backend.mocks.fixtures import PRIYA_AADHAAR, RAJESH_AADHAAR, REKHA_AADHAAR
from backend.state import create_initial_state, make_scheme_thread


def _never_called_chat_json(messages, **kwargs):
    raise AssertionError("chat_json should not have been called for this scenario")


def _state_with_thread(aadhaar_number, thread):
    state = create_initial_state(raw_input="test")
    state["user_profile"]["aadhaar_number"] = aadhaar_number
    state["scheme_threads"] = {thread["scheme_id"]: thread}
    return state


def test_all_docs_present_verifies_cleanly(monkeypatch):
    monkeypatch.setattr(validator_mod, "chat_json", _never_called_chat_json)

    thread = make_scheme_thread(
        "TN-EDUC-001", "State Merit Scholarship", 0.9,
        required_documents=["aadhaar_card", "income_certificate"],
    )
    state = _state_with_thread(REKHA_AADHAAR, thread)

    result = validator_mod.run_validator(state)
    updated = result["scheme_threads"]["TN-EDUC-001"]

    assert updated["phase"] == "docs_ready"
    assert updated["blocked_on"] == []
    assert all(d["status"] == "verified" for d in updated["documents"])

    actions = [step["action"] for step in result["reasoning_log"]]
    assert actions.count("doc_verified") == 2


def test_conflicting_docs_llm_resolves(monkeypatch):
    def fake_chat_json(messages, **kwargs):
        return {
            "admissible_record": "TN-LAND-THJ-2023-9910",
            "rationale": "The 2023 resurvey record is the most recent and supersedes the 2019 one",
            "confidence": 0.9,
        }

    monkeypatch.setattr(validator_mod, "chat_json", fake_chat_json)

    thread = make_scheme_thread(
        "TN-AGRI-002", "Farmer Input Subsidy", 0.85,
        required_documents=["aadhaar_card", "land_records", "bank_passbook"],
    )
    state = _state_with_thread(RAJESH_AADHAAR, thread)

    result = validator_mod.run_validator(state)
    updated = result["scheme_threads"]["TN-AGRI-002"]

    assert updated["phase"] == "docs_ready"
    assert updated["blocked_on"] == []
    land_doc = next(d for d in updated["documents"] if d["document_type"] == "land_records")
    assert land_doc["status"] == "verified"

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "doc_conflict_resolved" in actions


def test_missing_doc_fallback_recovers(monkeypatch):
    monkeypatch.setattr(validator_mod, "chat_json", _never_called_chat_json)

    thread = make_scheme_thread(
        "TN-HOUS-001", "Housing Scheme", 0.8,
        required_documents=["aadhaar_card", "land_patta_documents", "bank_passbook"],
        fallback_documents=[
            {"primary_doc": "land_patta_documents", "acceptable_alternatives": ["chitta_adangal", "village_adangal"]},
        ],
    )
    state = _state_with_thread(RAJESH_AADHAAR, thread)

    result = validator_mod.run_validator(state)
    updated = result["scheme_threads"]["TN-HOUS-001"]

    assert updated["phase"] == "docs_ready"
    assert updated["blocked_on"] == []
    patta_doc = next(d for d in updated["documents"] if d["document_type"] == "land_patta_documents")
    assert patta_doc["status"] == "verified"
    assert "fallback" in patta_doc["notes"]

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "doc_recovered_via_fallback" in actions


def test_missing_doc_no_fallback_blocks(monkeypatch):
    monkeypatch.setattr(validator_mod, "chat_json", _never_called_chat_json)

    thread = make_scheme_thread(
        "X-999", "Crafted Scheme", 0.7,
        required_documents=["nonexistent_document_type"],
    )
    state = _state_with_thread(PRIYA_AADHAAR, thread)

    result = validator_mod.run_validator(state)
    updated = result["scheme_threads"]["X-999"]

    assert updated["phase"] == "docs_blocked"
    assert updated["blocked_on"] == ["nonexistent_document_type"]

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "doc_missing_no_fallback" in actions


def test_llm_failure_marks_blocked_never_crashes(monkeypatch):
    def _raise(messages, **kwargs):
        raise RuntimeError("Featherless is unreachable")

    monkeypatch.setattr(validator_mod, "chat_json", _raise)

    thread = make_scheme_thread(
        "TN-AGRI-002", "Farmer Input Subsidy", 0.85,
        required_documents=["aadhaar_card", "land_records", "bank_passbook"],
    )
    state = _state_with_thread(RAJESH_AADHAAR, thread)

    result = validator_mod.run_validator(state)
    updated = result["scheme_threads"]["TN-AGRI-002"]

    assert updated["phase"] == "docs_blocked"
    assert "land_records" in updated["blocked_on"]

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "doc_conflict_unresolvable" in actions
