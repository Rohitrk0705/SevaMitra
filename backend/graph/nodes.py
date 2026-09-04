"""
backend/graph/nodes.py

Node functions for the SevaMithra LangGraph orchestrator. discovery_node is
real logic as of Rung 8 (thin wrapper around backend.agents.discovery.
run_discovery); verification_node, execution_node, monitor_node, and
escalate_node remain no-op placeholders pending Rungs 9-10.

SCHEMA DRIFT — RESOLVED in Rung 8: every phase string assigned by the stubs
below now uses the exact SchemePhase / current_phase Literal values declared
in backend/state.py ("matched" -> "discovered", "documents_verified" ->
"docs_ready", "submitted" -> "filed", "rti_drafted" -> "escalated_rti",
"monitor" -> "monitoring", "escalate" -> "escalation"). Each remapping is
noted inline at its assignment.
"""

from datetime import datetime, timezone

from backend.agents.discovery import run_discovery
from backend.state import SevaState, make_reasoning_step


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def trigger_node(state: SevaState) -> dict:
    raw_input = state["user_profile"]["raw_input"]
    step = make_reasoning_step(
        agent="trigger",
        action="parse_input",
        detail=(
            f"[STUB] Received raw user input ({len(raw_input)} chars) and did "
            "nothing further with it. Real Trigger node will call the LLM "
            "wrapper (backend.llm.chat_json) to extract a structured "
            "UserProfile from voice/text input."
        ),
    )
    return {
        "current_phase": "trigger",
        "reasoning_log": [step],
        "updated_at": _now_iso(),
    }


def discovery_node(state: SevaState) -> dict:
    """Thin LangGraph adapter around backend.agents.discovery.run_discovery.

    run_discovery is a pure function that returns a full mutated SevaState
    (see its docstring). scheme_threads and pursued_scheme_ids have no
    reducer in SevaState, so they're returned wholesale (last-write-wins);
    reasoning_log IS reduced via Annotated[list, add], so only the newly
    appended steps are returned here to avoid double-appending.
    """
    result_state = run_discovery(state)
    new_steps = result_state["reasoning_log"][len(state["reasoning_log"]):]

    return {
        "current_phase": "discovery",
        "scheme_threads": result_state["scheme_threads"],
        "pursued_scheme_ids": result_state["pursued_scheme_ids"],
        "discovery_status": result_state.get("discovery_status"),
        "reasoning_log": new_steps,
        "updated_at": result_state["updated_at"],
    }


def verification_node(state: SevaState) -> dict:
    updated_threads = {}
    for scheme_id, thread in state["scheme_threads"].items():
        updated = dict(thread)
        # Rung 8 drift fix: stub used "documents_verified", which has no
        # SchemePhase Literal equivalent. Closest existing member is
        # "docs_ready" (documents checked, ready to proceed).
        updated["phase"] = "docs_ready"
        updated_threads[scheme_id] = updated

    step = make_reasoning_step(
        agent="verification",
        action="verify_documents",
        detail=(
            "[STUB] Marked every scheme thread as documents_verified without "
            "checking any actual document. Real Validator node will call the "
            "mock DigiLocker endpoint (backend.mocks.api) for each required "
            "document and branch on missing/expired/mismatched status."
        ),
    )
    return {
        "current_phase": "verification",
        "scheme_threads": updated_threads,
        "reasoning_log": [step],
        "updated_at": _now_iso(),
    }


def execution_node(state: SevaState) -> dict:
    updated_threads = {}
    for scheme_id, thread in state["scheme_threads"].items():
        updated = dict(thread)
        # Rung 8 drift fix: stub used "submitted", which has no SchemePhase
        # Literal equivalent. Closest existing member is "filed".
        updated["phase"] = "filed"
        updated["application_id"] = f"APP-{scheme_id}-STUB"
        updated_threads[scheme_id] = updated

    step = make_reasoning_step(
        agent="execution",
        action="submit_application",
        detail=(
            "[STUB] Assigned a fake application_id to every scheme thread "
            "without submitting anything. Real Filler node will assemble the "
            "application payload from the verified documents and POST it to "
            "the mock applications/submit endpoint (backend.mocks.api)."
        ),
    )
    return {
        "current_phase": "execution",
        "scheme_threads": updated_threads,
        "reasoning_log": [step],
        "updated_at": _now_iso(),
    }


def monitor_node(state: SevaState) -> dict:
    now = _now_iso()
    updated_threads = {}
    for scheme_id, thread in state["scheme_threads"].items():
        updated = dict(thread)
        updated["phase"] = "monitoring"
        # SevaState has no top-level "monitor_started_at" field, and
        # backend/state.py is out of scope for this rung, so the start
        # timestamp is recorded on the already-declared per-thread field
        # closest in meaning: last_status_check_at.
        updated["last_status_check_at"] = now
        updated_threads[scheme_id] = updated

    step = make_reasoning_step(
        agent="monitor",
        action="begin_monitoring",
        detail=(
            "[STUB] Flagged every scheme thread as monitoring and stamped "
            "last_status_check_at. Does NOT actually wait. Real Monitor Agent "
            "(Rung 10) uses the SqliteSaver checkpointer to pause the graph, "
            "sleep past the Citizen Charter deadline, wake up autonomously, "
            "and check status via the mock applications/status endpoint."
        ),
    )
    return {
        # Rung 8 drift fix: stub used "monitor", which has no SevaState
        # current_phase Literal equivalent. state.py declares "monitoring".
        "current_phase": "monitoring",
        "scheme_threads": updated_threads,
        "reasoning_log": [step],
        "updated_at": now,
    }


def escalate_node(state: SevaState) -> dict:
    updated_threads = {}
    for scheme_id, thread in state["scheme_threads"].items():
        updated = dict(thread)
        # Rung 8 drift fix: stub used "rti_drafted", which has no SchemePhase
        # Literal equivalent. Closest existing member is "escalated_rti"
        # (drafted and escalated to the RTI track; not yet "rti_sent").
        updated["phase"] = "escalated_rti"
        # Rung 6 spec calls this field "rti_markdown"; backend/state.py's
        # SchemeThread already declares "rti_draft" for this purpose, so
        # that existing field is used rather than adding an undeclared key.
        updated["rti_draft"] = "[stub RTI content]"
        updated_threads[scheme_id] = updated

    step = make_reasoning_step(
        agent="escalate",
        action="draft_rti",
        detail=(
            "[STUB] Wrote placeholder text into rti_draft for every scheme "
            "thread instead of drafting anything real. Real Escalation node "
            "will call backend.rti.renderer to produce a filing-ready Tier-1 "
            "grievance email and Tier-2 RTI application from the verified "
            "clause corpus in backend/rti/clauses.json."
        ),
    )
    return {
        # Rung 8 drift fix: stub used "escalate", which has no SevaState
        # current_phase Literal equivalent. state.py declares "escalation".
        "current_phase": "escalation",
        "scheme_threads": updated_threads,
        "reasoning_log": [step],
        "updated_at": _now_iso(),
    }
