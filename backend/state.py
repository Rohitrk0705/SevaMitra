"""
backend/state.py

SevaMithra shared state schema — the single source of truth that flows
between all LangGraph agent nodes.

Design principles:
- Every field an agent reads or writes must be declared here.
- Everything is JSON-serializable (LangGraph SqliteSaver requirement).
- Per-scheme lifecycle is tracked in scheme_threads, keyed by scheme_id,
  so multiple schemes can be in different stages concurrently.
- reasoning_log is append-only and streamed to the frontend via SSE.
"""

from typing import TypedDict, Literal, Annotated, Optional
from operator import add


# ---------- Sub-schemas ----------

class UserProfile(TypedDict):
    """Extracted from voice/text input by the Trigger node."""
    name: str
    age: Optional[int]
    gender: Optional[Literal["male", "female", "other"]]
    occupation: list[str]
    annual_income_inr: Optional[int]
    landholding_hectares: Optional[float]
    state: str
    rural_urban: Optional[Literal["rural", "urban"]]
    category: Optional[Literal["general", "sc", "st", "obc", "ews", "minority"]]
    disability: bool
    marital_status: Optional[Literal["single", "married", "widowed", "divorced"]]
    family_composition: str
    raw_input: str


class SchemeMatch(TypedDict):
    """One scheme the Discovery agent flagged as a match candidate."""
    scheme_id: str
    scheme_name: str
    confidence: float
    reason: str
    required_documents: list[str]


class DocumentStatus(TypedDict):
    """Verification result for one document against mock DigiLocker."""
    document_type: str
    status: Literal["verified", "missing", "expired", "mismatch", "pending"]
    source: str
    last_checked_at: str
    notes: str


SchemePhase = Literal[
    "discovered",
    "verifying",
    "docs_ready",
    "docs_blocked",
    "filed",
    "monitoring",
    "response_received",
    "deadline_missed",
    "escalated_email",
    "escalated_rti",
    "rti_sent",
    "resolved",
    "abandoned",
]


class SchemeThread(TypedDict):
    """Full lifecycle state for one scheme the agent is pursuing."""
    scheme_id: str
    scheme_name: str
    phase: SchemePhase
    confidence: float
    blocked_on: list[str]
    documents: list[DocumentStatus]
    application_id: Optional[str]
    filed_at: Optional[str]
    charter_deadline_days: Optional[int]
    deadline_at: Optional[str]
    escalation_email_draft: Optional[str]
    rti_draft: Optional[str]
    rti_cited_clause: Optional[str]
    last_status_check_at: Optional[str]
    last_status_response: Optional[str]
    error: Optional[str]


class ReasoningStep(TypedDict):
    """One entry in the append-only reasoning log. Streamed to frontend."""
    timestamp: str
    agent: str
    action: str
    detail: str
    scheme_id: Optional[str]


# ---------- The main state ----------

class SevaState(TypedDict):
    """
    The single state dict flowing through the entire LangGraph.
    Every agent node accepts SevaState and returns a partial SevaState update.
    """
    user_profile: UserProfile
    candidate_schemes: list[SchemeMatch]
    pursued_scheme_ids: list[str]
    scheme_threads: dict[str, SchemeThread]
    reasoning_log: Annotated[list[ReasoningStep], add]
    current_phase: Literal[
        "trigger", "discovery", "verification",
        "execution", "monitoring", "escalation", "done"
    ]
    is_paused_for_timer: bool
    is_paused_for_user_auth: bool
    error: Optional[str]
    session_id: str
    created_at: str
    updated_at: str
    # Set only when Discovery exhausts both threshold passes (0.7, then 0.5)
    # with zero pursued schemes. None otherwise — added in Rung 8.
    discovery_status: Optional[Literal["no_matches"]]


# ---------- Helpers ----------

from datetime import datetime, timezone
import uuid


def _now_iso() -> str:
    """UTC ISO timestamp — used consistently across all state mutations."""
    return datetime.now(timezone.utc).isoformat()


def create_initial_state(raw_input: str, session_id: Optional[str] = None) -> SevaState:
    """Build a fresh SevaState from a user's raw input. Called by Trigger node."""
    now = _now_iso()
    return SevaState(
        user_profile=UserProfile(
            name="",
            age=None,
            gender=None,
            occupation=[],
            annual_income_inr=None,
            landholding_hectares=None,
            state="",
            rural_urban=None,
            category=None,
            disability=False,
            marital_status=None,
            family_composition="",
            raw_input=raw_input,
        ),
        candidate_schemes=[],
        pursued_scheme_ids=[],
        scheme_threads={},
        reasoning_log=[],
        current_phase="trigger",
        is_paused_for_timer=False,
        is_paused_for_user_auth=False,
        error=None,
        session_id=session_id or str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        discovery_status=None,
    )


def make_reasoning_step(
    agent: str,
    action: str,
    detail: str,
    scheme_id: Optional[str] = None,
) -> ReasoningStep:
    """Build one reasoning log entry. Agents use this before appending to state."""
    return ReasoningStep(
        timestamp=_now_iso(),
        agent=agent,
        action=action,
        detail=detail,
        scheme_id=scheme_id,
    )


def make_scheme_thread(
    scheme_id: str,
    scheme_name: str,
    confidence: float,
    charter_deadline_days: Optional[int] = None,
    blocked_on: Optional[list[str]] = None,
) -> SchemeThread:
    """Build a fresh SchemeThread when Discovery decides to pursue a scheme."""
    return SchemeThread(
        scheme_id=scheme_id,
        scheme_name=scheme_name,
        phase="discovered",
        confidence=confidence,
        blocked_on=blocked_on or [],
        documents=[],
        application_id=None,
        filed_at=None,
        charter_deadline_days=charter_deadline_days,
        deadline_at=None,
        escalation_email_draft=None,
        rti_draft=None,
        rti_cited_clause=None,
        last_status_check_at=None,
        last_status_response=None,
        error=None,
    )
