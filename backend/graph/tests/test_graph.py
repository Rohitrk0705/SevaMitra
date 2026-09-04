"""
pytest suite for backend/graph. Every test uses a fresh uuid4 thread_id
against the shared backend/graph/checkpoints.sqlite file, so runs never
cross-contaminate each other's state.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.graph.builder import build_graph
from backend.state import create_initial_state, make_reasoning_step, make_scheme_thread


def _fresh_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def _fake_discovery_matched(state):
    """Deterministic single-match discovery stub for tests that exercise
    graph wiring/checkpointing rather than Discovery's own matching logic
    (that's covered by tests/test_discovery_agent.py). Avoids depending on
    live ChromaDB/Featherless calls for plumbing tests, same as Rung 8's
    tests/test_graph_smoke.py.
    """
    scheme_id = "PM-KISAN"
    thread = make_scheme_thread(
        scheme_id=scheme_id,
        scheme_name="PM Kisan Samman Nidhi",
        confidence=0.85,
    )
    step = make_reasoning_step(
        agent="discovery",
        action="match_schemes",
        detail="[TEST-STUB] Deterministic single match to exercise graph plumbing.",
        scheme_id=scheme_id,
    )
    return {
        "current_phase": "discovery",
        "scheme_threads": {scheme_id: thread},
        "pursued_scheme_ids": [scheme_id],
        "reasoning_log": [step],
    }


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_full_happy_path(monkeypatch):
    monkeypatch.setattr("backend.graph.builder.discovery_node", _fake_discovery_matched)

    graph = build_graph()
    config = _fresh_config()
    state = create_initial_state(raw_input="farmer needs help")

    result = graph.invoke(state, config=config)

    assert len(result["scheme_threads"]) == 1
    thread = result["scheme_threads"]["PM-KISAN"]
    assert thread["phase"] == "escalated_rti"
    assert len(result["reasoning_log"]) >= 6
    assert result["current_phase"] == "escalation"


def test_checkpointer_persists(monkeypatch):
    monkeypatch.setattr("backend.graph.builder.discovery_node", _fake_discovery_matched)

    graph = build_graph()
    config = _fresh_config()
    state = create_initial_state(raw_input="farmer needs help")
    graph.invoke(state, config=config)

    # Fresh build_graph() call = fresh sqlite3 connection to the same file,
    # proving the checkpoint round-tripped through disk rather than staying
    # in the first graph object's memory.
    reloaded_graph = build_graph()
    reloaded_state = reloaded_graph.get_state(config)

    assert reloaded_state.values["current_phase"] == "escalation"
    assert len(reloaded_state.values["scheme_threads"]) == 1


def test_resume_from_checkpoint(monkeypatch):
    """Exercises the pause/resume seam the real Monitor Agent will use in
    Rung 10: interrupt_before pauses the graph before a node runs, leaving
    a resumable checkpoint; invoke(None, config) continues from there.
    """
    monkeypatch.setattr("backend.graph.builder.discovery_node", _fake_discovery_matched)

    graph = build_graph(interrupt_before=["escalate"])
    config = _fresh_config()
    state = create_initial_state(raw_input="farmer needs help")

    graph.invoke(state, config=config)
    paused = graph.get_state(config)

    assert "escalate" in paused.next
    assert paused.values["current_phase"] == "monitoring"
    assert paused.values["scheme_threads"]["PM-KISAN"]["phase"] == "monitoring"

    graph.invoke(None, config=config)
    resumed = graph.get_state(config)

    assert resumed.next == ()
    assert resumed.values["current_phase"] == "escalation"
    assert resumed.values["scheme_threads"]["PM-KISAN"]["phase"] == "escalated_rti"


def test_empty_discovery_skips_to_end(monkeypatch):
    def fake_discovery_node(state):
        step = make_reasoning_step(
            agent="discovery",
            action="match_schemes",
            detail="[STUB-TEST] Forced an empty match set to exercise should_verify's end route.",
        )
        return {
            "current_phase": "discovery",
            "scheme_threads": {},
            "reasoning_log": [step],
        }

    monkeypatch.setattr("backend.graph.builder.discovery_node", fake_discovery_node)

    graph = build_graph()
    config = _fresh_config()
    state = create_initial_state(raw_input="no matching schemes for this profile")

    result = graph.invoke(state, config=config)

    assert result["scheme_threads"] == {}
    assert result["current_phase"] == "discovery"
    agents_touched = {step["agent"] for step in result["reasoning_log"]}
    assert agents_touched == {"trigger", "discovery"}


def test_reasoning_log_ordering(monkeypatch):
    monkeypatch.setattr("backend.graph.builder.discovery_node", _fake_discovery_matched)

    graph = build_graph()
    config = _fresh_config()
    state = create_initial_state(raw_input="farmer needs help")

    result = graph.invoke(state, config=config)

    expected_order = ["trigger", "discovery", "verification", "execution", "monitor", "escalate"]
    agents_in_order = [step["agent"] for step in result["reasoning_log"]]
    assert agents_in_order == expected_order

    timestamps = [step["timestamp"] for step in result["reasoning_log"]]
    assert timestamps == sorted(timestamps)
