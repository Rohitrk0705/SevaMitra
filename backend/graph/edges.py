"""
backend/graph/edges.py

Conditional edge functions for the SevaMithra graph. Routing logic here is
deliberately trivial for now — these are the seams where Rungs 8-10 attach
real branching (e.g. loop monitor <-> escalate based on an actual Citizen
Charter deadline check instead of always escalating).
"""

from backend.state import SevaState


def should_verify(state: SevaState) -> str:
    """Routes to verification if Discovery matched at least one scheme, else ends."""
    if not state.get("scheme_threads"):
        return "end"
    return "verification"


def should_escalate(state: SevaState) -> str:
    """Always routes to escalate for now.

    Real Rung 10 logic will check whether any scheme_thread is still in the
    "monitoring" phase past its Citizen Charter deadline before deciding to
    escalate vs. keep waiting vs. mark resolved.
    """
    return "escalate"
