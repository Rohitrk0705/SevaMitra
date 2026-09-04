"""
tests/test_discovery_agent.py

Unit tests for backend.agents.discovery.run_discovery. These are hermetic:
backend.agents.discovery.query_schemes and .chat_json are monkeypatched to
controlled fixtures rather than hitting the live ChromaDB collection or
Featherless.

Two reasons this must be hermetic rather than integration-style:
  - backend/chroma_db/ is gitignored (local, rebuilt via
    `python -m backend.ingestion.ingest` from a raw data directory that
    also isn't in the repo) — it won't exist on a fresh checkout or in CI.
  - Real corpus distances for these personas mostly land structured-partial
    confidence (semantic_score * 0.6) *below* the 0.4 ambiguous floor, so a
    "sparse docs" candidate's blocked_on rarely survives into a pursued
    scheme_thread on the live data — verified by hand against the local
    corpus during development. Controlled fixtures let each test exercise
    the exact code path it's named for instead of depending on incidental
    real-corpus rankings that shift if the corpus is ever re-ingested.

Persona ages are computed from backend/mocks/fixtures.py's DOBs as of
today rather than the rung prompt's rounded labels ("62yo" etc.) — Priya's
DOB (1964-11-05) makes her 61, not 62, before her birthday.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.agents.discovery as discovery_mod
from backend.state import create_initial_state


def _candidate(scheme_id, name, category, distance, **overrides):
    base = {
        "scheme_id": scheme_id,
        "name": name,
        "description": f"{name} description.",
        "department": "Test Department",
        "state": "Tamil Nadu",
        "category": category,
        "target_beneficiaries": "general public",
        "eligibility_notes": "",
        "required_documents": [],
        "citizen_charter_days": 30,
        "income_max": None,
        "age_min": None,
        "age_max": None,
        "landholding_max_hectares": None,
        "gender": None,
        "official_source_url": "",
        "distance": distance,
    }
    base.update(overrides)
    return base


def _always_pursue(confidence=0.85, rationale="Profile broadly satisfies the scheme's criteria"):
    def _fake_chat_json(messages, **kwargs):
        return {"verdict": "pursue", "confidence": confidence, "rationale": rationale}
    return _fake_chat_json


def _always_reject(rationale="Not enough matching information to justify pursuing this"):
    def _fake_chat_json(messages, **kwargs):
        return {"verdict": "reject", "confidence": 0.1, "rationale": rationale}
    return _fake_chat_json


def _rekha_profile():
    state = create_initial_state(
        raw_input=(
            "I am 18 years old, an OBC student from Coimbatore, Tamil Nadu. My "
            "family's income is low and I need a scholarship to continue my education."
        )
    )
    profile = state["user_profile"]
    profile.update(
        age=18,
        gender="female",
        occupation=["student"],
        annual_income_inr=84000,
        state="Tamil Nadu",
        rural_urban="urban",
        category="obc",
        marital_status="single",
        family_composition="farmer's daughter",
    )
    return state


def _rajesh_profile():
    state = create_initial_state(
        raw_input=(
            "I am a 45 year old farmer in Thanjavur, Tamil Nadu, with 2 acres of "
            "land. I need support for my crops."
        )
    )
    profile = state["user_profile"]
    profile.update(
        age=45,
        gender="male",
        occupation=["farmer"],
        annual_income_inr=145000,
        landholding_hectares=0.8,
        state="Tamil Nadu",
        rural_urban="rural",
        marital_status="married",
        family_composition="spouse and two children",
    )
    return state


def _priya_profile():
    # Sparse docs: no income, no landholding, no category — matches the
    # persona ("wildcard: sparse docs") in backend/mocks/fixtures.py.
    state = create_initial_state(
        raw_input=(
            "I am a widow in Tamil Nadu. My husband passed away and I need "
            "financial support."
        )
    )
    profile = state["user_profile"]
    profile.update(
        age=61,
        gender="female",
        state="Tamil Nadu",
        rural_urban="rural",
        marital_status="widowed",
    )
    return state


def test_rekha_matches_scholarships(monkeypatch):
    candidates = [
        # Directly clears 0.7 without a tie-break: distance 0.3 -> semantic
        # 1/1.3=0.769, full match (no structured constraints on this one).
        _candidate("TN-EDUC-001", "State Merit Scholarship", "education", 0.3),
        # Ambiguous full match (income_max 250000 >= Rekha's 84000):
        # distance 0.6 -> semantic 0.625, base 0.625 -> tie-break needed.
        _candidate("TN-EDUC-002", "Post-Matric OBC Scholarship", "education", 0.6, income_max=250000),
        # Structural mismatch: Rekha's income (84000) exceeds this cap.
        _candidate("IN-EDUC-003", "Ultra Low Income Scholarship", "education", 0.5, income_max=10000),
        # Irrelevant low-confidence noise, never reaches the ambiguous band.
        _candidate("TN-MISC-004", "Unrelated Scheme", "other", 3.0),
    ]
    monkeypatch.setattr(discovery_mod, "query_schemes", lambda text, n_results=15: candidates)
    monkeypatch.setattr(discovery_mod, "chat_json", _always_pursue(confidence=0.9))

    result = discovery_mod.run_discovery(_rekha_profile())

    scholarship_ids = {"TN-EDUC-001", "TN-EDUC-002"}
    pursued_scholarships = [
        t for sid, t in result["scheme_threads"].items()
        if sid in scholarship_ids and t["confidence"] >= 0.7
    ]
    assert len(pursued_scholarships) >= 2
    assert "IN-EDUC-003" not in result["scheme_threads"]


def test_rajesh_matches_agriculture(monkeypatch):
    candidates = [
        _candidate("IN-AGRI-001", "PM Kisan Samman Nidhi", "agriculture", 0.25),
        _candidate(
            "TN-AGRI-002", "Farmer Input Subsidy", "agriculture", 0.6,
            landholding_max_hectares=2.0,
        ),
        # Landholding cap Rajesh's 0.8 hectares clears easily but far away
        # semantically, plus low base confidence.
        _candidate("TN-MISC-003", "Unrelated Scheme", "other", 3.0),
    ]
    monkeypatch.setattr(discovery_mod, "query_schemes", lambda text, n_results=15: candidates)
    monkeypatch.setattr(discovery_mod, "chat_json", _always_pursue(confidence=0.88))

    result = discovery_mod.run_discovery(_rajesh_profile())

    agri_pursued = [
        t for sid, t in result["scheme_threads"].items()
        if sid in {"IN-AGRI-001", "TN-AGRI-002"} and t["confidence"] >= 0.7
    ]
    assert len(agri_pursued) >= 2


def test_priya_partial_block(monkeypatch):
    candidates = [
        # Full match, clears 0.7 directly: no income/age constraint set.
        _candidate("TN-SOCL-001", "Destitute Widow Pension", "social_welfare", 0.3, age_min=18),
        # Partial match: income_max is set but Priya's annual_income_inr is
        # None (sparse docs) -> blocked_on=["annual_income_inr"]. distance
        # 0.2 -> semantic 0.833, base 0.833*0.6=0.5 -> ambiguous -> tie-break.
        _candidate(
            "TN-SOCL-002", "Marriage Assistance for Widows", "social_welfare", 0.2,
            income_max=72000,
        ),
    ]
    monkeypatch.setattr(discovery_mod, "query_schemes", lambda text, n_results=15: candidates)
    monkeypatch.setattr(discovery_mod, "chat_json", _always_pursue(confidence=0.75))

    result = discovery_mod.run_discovery(_priya_profile())

    assert len(result["scheme_threads"]) >= 1
    assert any(t["scheme_id"] == "TN-SOCL-001" for t in result["scheme_threads"].values())

    blocked = [t for t in result["scheme_threads"].values() if t["blocked_on"]]
    assert len(blocked) >= 1
    assert "annual_income_inr" in blocked[0]["blocked_on"]


def test_no_matches_expands_threshold(monkeypatch):
    candidates = [
        # Mismatch: hard reject regardless of threshold.
        _candidate("X-001", "Wrong Gender Scheme", "other", 0.3, gender="male"),
        # Full match but too far semantically to ever clear 0.4.
        _candidate("X-002", "Distant Scheme", "other", 6.0),
    ]
    monkeypatch.setattr(discovery_mod, "query_schemes", lambda text, n_results=15: candidates)
    monkeypatch.setattr(discovery_mod, "chat_json", _always_reject())

    state = _priya_profile()
    result = discovery_mod.run_discovery(state)

    assert result["scheme_threads"] == {}
    assert result["discovery_status"] == "no_matches"
    actions = [step["action"] for step in result["reasoning_log"]]
    assert "threshold_expanded" in actions
    assert "no_matches_found" in actions


def test_llm_failure_defaults_to_reject(monkeypatch):
    candidates = [
        # High-confidence, never touches the LLM — proves a tie-break
        # failure doesn't take down the whole run.
        _candidate("TN-SAFE-001", "Safe High-Confidence Scheme", "other", 0.25),
        # Ambiguous -> routed to the (broken) tie-break.
        _candidate("TN-AMBIG-002", "Ambiguous Scheme", "other", 0.6),
    ]
    monkeypatch.setattr(discovery_mod, "query_schemes", lambda text, n_results=15: candidates)

    def _raise(*args, **kwargs):
        raise RuntimeError("Featherless is unreachable")

    monkeypatch.setattr(discovery_mod, "chat_json", _raise)

    result = discovery_mod.run_discovery(_rekha_profile())

    assert "TN-AMBIG-002" not in result["scheme_threads"]
    assert "TN-SAFE-001" in result["scheme_threads"]

    actions = [step["action"] for step in result["reasoning_log"]]
    assert "llm_error" in actions


def test_reasoning_log_stream_readable(monkeypatch):
    candidates = [
        _candidate("TN-EDUC-001", "State Merit Scholarship", "education", 0.3),
        _candidate("TN-EDUC-002", "Post-Matric OBC Scholarship", "education", 0.6, income_max=250000),
    ]
    monkeypatch.setattr(discovery_mod, "query_schemes", lambda text, n_results=15: candidates)
    monkeypatch.setattr(discovery_mod, "chat_json", _always_pursue())

    result = discovery_mod.run_discovery(_rekha_profile())

    assert len(result["reasoning_log"]) > 0
    for step in result["reasoning_log"]:
        assert step["agent"] == "discovery"
        assert step["timestamp"]
        assert step["action"]
        detail = step["detail"]
        assert detail and detail.strip()
        assert detail.strip()[-1] in ".!?", f"detail doesn't read as a full sentence: {detail!r}"
