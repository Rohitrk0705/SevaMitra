"""
tests/test_graph_smoke.py

Lightweight smoke test for the SevaMithra LangGraph orchestrator: proves the
graph compiles and every node writes an exact SchemePhase / current_phase
Literal from backend/state.py (Rung 8 schema-drift reconciliation).

discovery_node is monkeypatched to a deterministic stub so this test stays
fast and offline (no ChromaDB or Featherless calls) and doesn't depend on
Discovery's real matching behavior — that's covered separately by
tests/test_discovery_agent.py. Full pipeline coverage (checkpoint
persistence, pause/resume) lives in backend/graph/tests/test_graph.py.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.graph.builder import build_graph
from backend.state import create_initial_state, make_reasoning_step, make_scheme_thread


def _fresh_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def _fake_discovery_node(state):
    scheme_id = "PM-KISAN"
    thread = make_scheme_thread(
        scheme_id=scheme_id,
        scheme_name="PM Kisan Samman Nidhi",
        confidence=0.85,
    )
    step = make_reasoning_step(
        agent="discovery",
        action="match_schemes",
        detail="[SMOKE-TEST] Deterministic single match to exercise phase wiring.",
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


def test_all_six_nodes_write_reconciled_phase_literals(monkeypatch):
    monkeypatch.setattr("backend.graph.builder.discovery_node", _fake_discovery_node)

    graph = build_graph()
    config = _fresh_config()
    state = create_initial_state(raw_input="farmer needs help")

    result = graph.invoke(state, config=config)

    agents_in_order = [step["agent"] for step in result["reasoning_log"]]
    assert agents_in_order == [
        "trigger",
        "discovery",
        "verification",
        "execution",
        "monitor",
        "escalate",
    ]

    thread = result["scheme_threads"]["PM-KISAN"]
    assert thread["phase"] == "escalated_rti"
    assert result["current_phase"] == "escalation"
