"""
tests/test_divergent_personas.py

End-to-end Discovery -> Validator -> Filler across the three demo
personas. Discovery's query_schemes is monkeypatched to controlled
candidates (same rationale as tests/test_discovery_agent.py: the live
ChromaDB collection is gitignored/rebuilt locally, not hermetic). From
there, Validator and Filler run against the REAL backend.mocks.fixtures
persona data — that's the whole point of Rung 9's fixture work. Only
chat_json (Featherless) is monkeypatched, via a single dispatching fake
that inspects which prompt template is asking (discovery tie-break vs.
Validator's doc-conflict resolution vs. Filler's field inference) so one
function can stand in for all three call sites across all three agent
modules.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.agents.discovery as discovery_mod
import backend.agents.filler as filler_mod
import backend.agents.validator as validator_mod
from backend.mocks.fixtures import PRIYA_AADHAAR, RAJESH_AADHAAR, REKHA_AADHAAR
from backend.state import create_initial_state


def _candidate(scheme_id, name, category, required_documents, fallback_documents=None, distance=0.1):
    return {
        "scheme_id": scheme_id,
        "name": name,
        "description": f"{name} description.",
        "department": "Test Department",
        "state": "Tamil Nadu",
        "category": category,
        "target_beneficiaries": "general public",
        "eligibility_notes": "",
        "required_documents": required_documents,
        "fallback_documents": fallback_documents or [],
        "citizen_charter_days": 30,
        "income_max": None,
        "age_min": None,
        "age_max": None,
        "landholding_max_hectares": None,
        "gender": None,
        "official_source_url": "",
        "distance": distance,
    }


def _dispatching_chat_json(land_record_choice="TN-LAND-THJ-2023-9910"):
    """One fake chat_json good for all three agents' distinct prompts,
    picked by inspecting which schema_hint/system-prompt text is present.
    """
    def _fake(messages, **kwargs):
        text = " ".join(m.get("content", "") for m in messages)
        if "admissible_record" in text:
            return {
                "admissible_record": land_record_choice,
                "rationale": "The more recent resurvey record supersedes the older one",
                "confidence": 0.9,
            }
        if "cannot_infer" in text:
            return {
                "verdict": "cannot_infer",
                "value": None,
                "rationale": "A bank account number cannot be inferred from any document on file",
            }
        return {"verdict": "pursue", "confidence": 0.9, "rationale": "Profile broadly satisfies the scheme's criteria"}

    return _fake


def _run_full_flow(profile_overrides, candidates, monkeypatch):
    monkeypatch.setattr(discovery_mod, "query_schemes", lambda text, n_results=15: candidates)
    fake_chat_json = _dispatching_chat_json()
    monkeypatch.setattr(discovery_mod, "chat_json", fake_chat_json)
    monkeypatch.setattr(validator_mod, "chat_json", fake_chat_json)
    monkeypatch.setattr(filler_mod, "chat_json", fake_chat_json)

    state = create_initial_state(raw_input=profile_overrides.pop("raw_input", "test"))
    state["user_profile"].update(profile_overrides)

    state = discovery_mod.run_discovery(state)
    state = validator_mod.run_validator(state)
    state = filler_mod.run_filler(state)
    return state


def test_rekha_full_flow(monkeypatch):
    candidates = [
        _candidate("TN-EDUC-001", "State Merit Scholarship", "education", ["aadhaar_card", "income_certificate"]),
    ]
    result = _run_full_flow(
        {"name": "Rekha Murugan", "aadhaar_number": REKHA_AADHAAR, "age": 18, "state": "Tamil Nadu"},
        candidates,
        monkeypatch,
    )

    assert len(result["scheme_threads"]) == 1
    for thread in result["scheme_threads"].values():
        assert thread["phase"] == "filed"


def test_rajesh_full_flow(monkeypatch):
    candidates = [
        _candidate("TN-AGRI-001", "Clean Farmer Scheme", "agriculture", ["aadhaar_card", "bank_passbook"]),
        _candidate("TN-AGRI-002", "Land Records Subsidy", "agriculture", ["aadhaar_card", "land_records", "bank_passbook"]),
        _candidate(
            "TN-HOUS-001", "Housing Scheme", "social_welfare",
            ["aadhaar_card", "land_patta_documents", "bank_passbook"],
            fallback_documents=[
                {"primary_doc": "land_patta_documents", "acceptable_alternatives": ["chitta_adangal", "village_adangal"]},
            ],
        ),
    ]
    result = _run_full_flow(
        {"name": "Rajesh Kumar", "aadhaar_number": RAJESH_AADHAAR, "age": 45, "state": "Tamil Nadu"},
        candidates,
        monkeypatch,
    )

    assert len(result["scheme_threads"]) == 3
    for thread in result["scheme_threads"].values():
        assert thread["phase"] == "filed"

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "doc_conflict_resolved" in actions
    assert "doc_recovered_via_fallback" in actions


def test_priya_full_flow(monkeypatch):
    candidates = [
        _candidate("TN-SOCL-010", "Destitute Widow Pension", "social_welfare", ["aadhaar_card", "widow_certificate", "bpl_certificate"]),
    ]
    result = _run_full_flow(
        {"name": "Priya Sundaram", "aadhaar_number": PRIYA_AADHAAR, "age": 61, "state": "Tamil Nadu"},
        candidates,
        monkeypatch,
    )

    assert len(result["scheme_threads"]) == 1
    for thread in result["scheme_threads"].values():
        assert thread["phase"] == "filed"
