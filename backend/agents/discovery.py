"""
backend/agents/discovery.py

Real Discovery agent logic (Rung 8). Pure function — no LangGraph imports —
so it can be unit-tested directly against a SevaState without building or
invoking the graph. backend/graph/nodes.py's discovery_node is a thin
wrapper around run_discovery() that adapts its output to the partial-update
shape LangGraph node functions return.

Flow: build a semantic query from the citizen's profile -> retrieve top-15
candidates from ChromaDB -> run a structured eligibility check against each
candidate's flattened eligibility fields -> for ambiguous verdicts, tie-break
with a single Featherless LLM call -> filter to a confidence threshold
(0.7, retried once at 0.5 if nothing clears the bar) -> create SchemeThread
entries for whatever's left.

DEVIATIONS from the literal Rung 8 spec (flagged during planning, not
guessed silently):
  - The spec's "eligibility_structured" is the raw nested dict from the
    original scheme JSON. backend/ingestion/normalise.py flattens that dict
    into scalar NormalisedScheme fields (income_max, age_min, age_max,
    landholding_max_hectares, gender) before embedding into ChromaDB, and
    the raw nested form isn't retrievable — backend.ingestion.retrieve
    .query_schemes() never returns it. The structured check here runs
    against those flattened fields instead. Caste/category eligibility
    (SC/ST/OBC/EWS) has no structured field at all in the retrieved
    records — it only survives as free text in eligibility_notes /
    target_beneficiaries — so it feeds the semantic query but isn't part
    of the structured pass/fail check.
  - Chroma distance -> confidence uses semantic_score = 1 / (1 + distance),
    a metric-agnostic monotonic squash (the collection wasn't created with
    an explicit hnsw:space, so the distance metric isn't guaranteed to be
    cosine-bounded).
"""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.ingestion.retrieve import query_schemes
from backend.llm import chat_json
from backend.state import SevaState, UserProfile, make_reasoning_step, make_scheme_thread

N_CANDIDATES = 15  # [ASSUMPTION per spec] override if more/fewer are wanted
PRIMARY_THRESHOLD = 0.7  # [ASSUMPTION per spec, demo default]
EXPANDED_THRESHOLD = 0.5
AMBIGUOUS_LOW = 0.4
AMBIGUOUS_HIGH = 0.7
TIEBREAK_TEMPERATURE = 0.1

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "discovery_tiebreak.txt"

_STRUCTURED_RANK = {"ok": 0, "missing": 1, "mismatch": 2}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_sentence(text: str) -> str:
    """Guarantees reasoning-log detail text reads as a complete sentence
    when streamed line-by-line (Rung 11 SSE Agent Thought Stream)."""
    text = (text or "").strip()
    if not text:
        return text
    return text if text[-1] in ".!?" else text + "."


def _age_band(age: int) -> str:
    if age < 18:
        return "minor"
    if age < 25:
        return "youth"
    if age < 40:
        return "adult"
    if age < 60:
        return "middle-aged adult"
    return "senior citizen"


def _build_query_text(profile: UserProfile) -> str:
    """Builds the semantic search string. `name` is deliberately excluded.

    UserProfile has no dedicated `stated_need` field; `raw_input` (the
    citizen's own words) is the closest thing the schema has to it, so it
    stands in for "stated_need" here.
    """
    parts: list[str] = []

    occupation = profile.get("occupation") or []
    if occupation:
        parts.append(", ".join(occupation))

    age = profile.get("age")
    if age is not None:
        parts.append(_age_band(age))

    if profile.get("rural_urban"):
        parts.append(profile["rural_urban"])

    if profile.get("state"):
        parts.append(profile["state"])

    if profile.get("category"):
        parts.append(profile["category"])

    if profile.get("marital_status"):
        parts.append(profile["marital_status"])

    if profile.get("family_composition"):
        parts.append(profile["family_composition"])

    if profile.get("disability"):
        parts.append("person with disability")

    if profile.get("raw_input"):
        parts.append(profile["raw_input"])

    return " ".join(p for p in parts if p).strip()


def _summarise_profile(profile: UserProfile) -> str:
    bits = []
    if profile.get("age") is not None:
        bits.append(f"age {profile['age']}")
    if profile.get("gender"):
        bits.append(f"gender {profile['gender']}")
    if profile.get("occupation"):
        bits.append("occupation: " + ", ".join(profile["occupation"]))
    if profile.get("annual_income_inr") is not None:
        bits.append(f"annual income INR {profile['annual_income_inr']}")
    if profile.get("landholding_hectares") is not None:
        bits.append(f"landholding {profile['landholding_hectares']} hectares")
    if profile.get("category"):
        bits.append(f"category {profile['category']}")
    if profile.get("marital_status"):
        bits.append(f"marital status {profile['marital_status']}")
    if profile.get("family_composition"):
        bits.append(f"family: {profile['family_composition']}")
    if profile.get("state"):
        bits.append(f"state {profile['state']}")
    if profile.get("raw_input"):
        bits.append(f"in their own words: {profile['raw_input']}")
    return "; ".join(bits) if bits else "no structured profile fields available"


def _check_structured(candidate: dict, profile: UserProfile) -> tuple[str, list[str], Optional[str]]:
    """Runs the structured eligibility check against the flattened
    NormalisedScheme fields returned by ChromaDB retrieval.

    Returns (verdict, blocked_on, mismatch_reason) where verdict is one of
    "full" (every checkable field matches), "partial" (some fields are
    missing from the user profile), or "mismatch" (a provided field fails
    the rule -> hard reject).
    """
    field_status: dict[str, str] = {}
    reasons: dict[str, str] = {}

    def evaluate(scheme_val, user_val, predicate, label, rule_desc):
        if scheme_val is None:
            return
        if user_val is None:
            status = "missing"
        elif predicate(user_val, scheme_val):
            status = "ok"
        else:
            status = "mismatch"
            reasons[label] = (
                f"{label}={user_val!r} does not satisfy the {rule_desc} rule "
                f"(scheme requires {scheme_val!r})"
            )
        if label not in field_status or _STRUCTURED_RANK[status] > _STRUCTURED_RANK[field_status[label]]:
            field_status[label] = status

    evaluate(
        candidate.get("income_max"), profile.get("annual_income_inr"),
        lambda u, s: u <= s, "annual_income_inr", "maximum annual income",
    )
    evaluate(
        candidate.get("age_min"), profile.get("age"),
        lambda u, s: u >= s, "age", "minimum age",
    )
    evaluate(
        candidate.get("age_max"), profile.get("age"),
        lambda u, s: u <= s, "age", "maximum age",
    )
    evaluate(
        candidate.get("landholding_max_hectares"), profile.get("landholding_hectares"),
        lambda u, s: u <= s, "landholding_hectares", "maximum landholding",
    )
    evaluate(
        candidate.get("gender"), profile.get("gender"),
        lambda u, s: u == s or s in ("any", "all"), "gender", "gender eligibility",
    )

    if not field_status:
        return "full", [], None

    mismatched = [label for label, status in field_status.items() if status == "mismatch"]
    if mismatched:
        reason = "; ".join(reasons[label] for label in mismatched)
        return "mismatch", mismatched, reason

    missing = sorted(label for label, status in field_status.items() if status == "missing")
    if missing:
        return "partial", missing, None

    return "full", [], None


def _structured_confidence(verdict: str, semantic_score: float) -> float:
    if verdict == "mismatch":
        return 0.0
    if verdict == "full":
        return semantic_score * 1.0
    return semantic_score * 0.6  # partial


@lru_cache(maxsize=1)
def _load_tiebreak_template() -> str:
    return _PROMPT_PATH.read_text()


def _run_llm_tiebreak(candidate: dict, profile: UserProfile, base_confidence: float, blocked_on: list[str], log) -> float:
    scheme_id = candidate.get("scheme_id")
    name = candidate.get("name") or scheme_id

    prompt = _load_tiebreak_template().format(
        scheme_name=name,
        scheme_description=candidate.get("description") or "not available",
        eligibility_notes=candidate.get("eligibility_notes") or "not available",
        target_beneficiaries=candidate.get("target_beneficiaries") or "not specified",
        blocked_on=", ".join(blocked_on) or "none",
        user_profile_summary=_summarise_profile(profile),
        base_confidence=f"{base_confidence:.2f}",
    )

    try:
        result = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an eligibility tie-breaker for an Indian government "
                        "scheme discovery assistant. Respond with strict JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=TIEBREAK_TEMPERATURE,
            schema_hint='{"verdict": "pursue" | "reject", "confidence": float, "rationale": str}',
        )
    except Exception as exc:
        is_parse_failure = isinstance(exc, ValueError) and "failed to parse JSON" in str(exc)
        action = "llm_parse_failed" if is_parse_failure else "llm_error"
        log(
            action,
            f"The tie-break call for {name} failed ({exc}), so it defaults to rejected "
            "rather than risk pursuing a bad match",
            scheme_id=scheme_id,
        )
        return 0.0

    try:
        verdict = result["verdict"]
        confidence = float(result["confidence"])
        rationale = str(result["rationale"])
    except (KeyError, TypeError, ValueError) as exc:
        log(
            "llm_parse_failed",
            f"The tie-break response for {name} didn't match the expected shape ({exc}), "
            "so it defaults to rejected",
            scheme_id=scheme_id,
        )
        return 0.0

    if verdict != "pursue":
        log("llm_tiebreak", f"The tie-break check rejected {name}: {rationale}", scheme_id=scheme_id)
        return 0.0

    confidence = max(0.0, min(1.0, confidence))
    log("llm_tiebreak", f"The tie-break check leans toward pursuing {name}: {rationale}", scheme_id=scheme_id)
    return confidence


def _select_pursued(evaluated: list[dict], log) -> tuple[list[dict], float]:
    def at_threshold(threshold: float) -> list[dict]:
        return [e for e in evaluated if e["confidence"] >= threshold]

    pursued = at_threshold(PRIMARY_THRESHOLD)
    if pursued:
        return pursued, PRIMARY_THRESHOLD

    log(
        "threshold_expanded",
        f"No scheme cleared the standard {PRIMARY_THRESHOLD:.1f} confidence bar, so it "
        f"was lowered to {EXPANDED_THRESHOLD:.1f} to avoid missing a plausible match",
    )
    pursued = at_threshold(EXPANDED_THRESHOLD)
    return pursued, EXPANDED_THRESHOLD


def run_discovery(state: SevaState) -> SevaState:
    """Runs the full Discovery flow and returns a mutated copy of state.

    Note for callers inside the graph: this returns the FULL updated state
    (including the full reasoning_log), not a delta. backend/graph/nodes.py
    diffs reasoning_log against the input to produce the partial-update
    dict LangGraph's Annotated[list, add] reducer expects.
    """
    profile = state["user_profile"]
    reasoning_log = list(state["reasoning_log"])

    def log(action: str, detail: str, scheme_id: Optional[str] = None) -> None:
        reasoning_log.append(
            make_reasoning_step(
                agent="discovery",
                action=action,
                detail=_ensure_sentence(detail),
                scheme_id=scheme_id,
            )
        )

    query_text = _build_query_text(profile)
    if query_text:
        log(
            "query_constructed",
            "Built a search query from the citizen's occupation, age, location, and "
            f"family situation to look for matching schemes: {query_text}",
        )
    else:
        log(
            "query_constructed",
            "The citizen's profile has no usable fields yet, so the search query is "
            "empty; retrieval will likely surface generic results",
        )

    raw_candidates = query_schemes(query_text, n_results=N_CANDIDATES)
    top3_names = [c.get("name") or c.get("scheme_id") for c in raw_candidates[:3]]
    log(
        "semantic_retrieval",
        f"Searched the scheme database and found {len(raw_candidates)} possible matches, "
        f"with {', '.join(top3_names) or 'none'} among the closest. Each one will now be "
        "checked against eligibility rules",
    )

    evaluated: list[dict] = []
    for candidate in raw_candidates:
        scheme_id = candidate.get("scheme_id")
        name = candidate.get("name") or scheme_id
        distance = candidate.get("distance")
        semantic_score = 1.0 / (1.0 + max(distance or 0.0, 0.0))

        verdict, blocked_on, mismatch_reason = _check_structured(candidate, profile)

        if verdict == "mismatch":
            log("structured_check", f"Ruled out {name}: {mismatch_reason}", scheme_id=scheme_id)
            continue

        base_confidence = _structured_confidence(verdict, semantic_score)

        if blocked_on:
            log(
                "structured_check",
                f"{name} partially matches — missing profile information on "
                f"{', '.join(blocked_on)}, capping confidence at {base_confidence:.2f}",
                scheme_id=scheme_id,
            )
        else:
            log(
                "structured_check",
                f"{name} fully matches every structured eligibility rule that could be "
                f"checked, giving it a confidence of {base_confidence:.2f}",
                scheme_id=scheme_id,
            )

        if AMBIGUOUS_LOW <= base_confidence <= AMBIGUOUS_HIGH:
            final_confidence = _run_llm_tiebreak(candidate, profile, base_confidence, blocked_on, log)
        else:
            final_confidence = base_confidence

        evaluated.append(
            {
                "scheme_id": scheme_id,
                "name": name,
                "confidence": final_confidence,
                "blocked_on": blocked_on,
                "charter_deadline_days": candidate.get("citizen_charter_days"),
            }
        )

    pursued, threshold_used = _select_pursued(evaluated, log)

    scheme_threads = dict(state["scheme_threads"])
    pursued_scheme_ids = list(state["pursued_scheme_ids"])
    discovery_status = None

    if pursued:
        for entry in pursued:
            thread = make_scheme_thread(
                scheme_id=entry["scheme_id"],
                scheme_name=entry["name"],
                confidence=entry["confidence"],
                charter_deadline_days=entry["charter_deadline_days"],
                blocked_on=entry["blocked_on"],
            )
            scheme_threads[entry["scheme_id"]] = thread
            if entry["scheme_id"] not in pursued_scheme_ids:
                pursued_scheme_ids.append(entry["scheme_id"])

        names = ", ".join(e["name"] for e in pursued)
        log(
            "schemes_selected",
            f"Selected {len(pursued)} scheme(s) to pursue at the {threshold_used:.1f} "
            f"confidence bar: {names}",
        )
    else:
        discovery_status = "no_matches"
        log(
            "no_matches_found",
            f"After evaluating {len(raw_candidates)} candidates at both the "
            f"{PRIMARY_THRESHOLD:.1f} and {EXPANDED_THRESHOLD:.1f} confidence bars, none "
            "qualified, so no schemes are being pursued right now",
        )

    new_state = dict(state)
    new_state["scheme_threads"] = scheme_threads
    new_state["pursued_scheme_ids"] = pursued_scheme_ids
    new_state["reasoning_log"] = reasoning_log
    new_state["current_phase"] = "discovery"
    new_state["discovery_status"] = discovery_status
    new_state["updated_at"] = _now_iso()
    return new_state  # type: ignore[return-value]
