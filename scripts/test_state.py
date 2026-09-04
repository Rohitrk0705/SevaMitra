"""Proof that the SevaState schema and its helper functions work as intended."""

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.state import create_initial_state, make_reasoning_step, make_scheme_thread

state = create_initial_state(raw_input="I am a farmer with 2 acres")

step = make_reasoning_step(
    agent="trigger",
    action="parse_input",
    detail="Extracted raw input from user, awaiting profile enrichment.",
)
state["reasoning_log"].append(step)

thread = make_scheme_thread(
    scheme_id="IN-AGRI-001",
    scheme_name="PM-KISAN",
    confidence=0.85,
    charter_deadline_days=60,
)
state["scheme_threads"]["IN-AGRI-001"] = thread

print(json.dumps(state, default=str, indent=2))

assert uuid.UUID(state["session_id"]), "session_id is not a valid UUID"
assert len(state["reasoning_log"]) == 1, "reasoning_log should have exactly one entry"
assert state["scheme_threads"]["IN-AGRI-001"]["phase"] == "discovered", (
    "scheme thread phase should be 'discovered'"
)

print("\nAll assertions passed.")
