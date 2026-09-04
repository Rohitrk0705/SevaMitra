"""
backend/rti/renderer.py

Renders the Tier-1 escalation email and Tier-2 RTI application from the
pre-approved skeletons in backend/rti/templates/, filling in only
case-specific facts. Every statutory citation that appears in a rendered
document must trace back to an entry in backend/rti/clauses.json — this
module does not paraphrase or invent legal language.
"""

import json
from datetime import date
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

_MODULE_DIR = Path(__file__).resolve().parent
_CLAUSES_PATH = _MODULE_DIR / "clauses.json"
_TEMPLATES_DIR = _MODULE_DIR / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

_CLAUSES = json.loads(_CLAUSES_PATH.read_text())


def load_clauses() -> dict:
    """Returns the parsed clauses.json content."""
    return _CLAUSES


def get_clause(clause_id: str) -> dict:
    """Returns a single RTI Act clause by id. Raises KeyError if not found."""
    for clause in _CLAUSES["clauses"]:
        if clause["id"] == clause_id:
            return clause
    raise KeyError(f"No clause with id '{clause_id}' in clauses.json")


def get_charter(charter_id: str) -> dict:
    """Returns a single Citizen Charter entry by id. Raises KeyError if not found."""
    for charter in _CLAUSES["citizen_charters"]:
        if charter["id"] == charter_id:
            return charter
    raise KeyError(f"No citizen charter with id '{charter_id}' in clauses.json")


def _require(mapping: dict, keys: list, label: str) -> None:
    missing = [k for k in keys if mapping.get(k) in (None, "")]
    if missing:
        raise KeyError(
            f"Missing required {label} field(s): {missing}. "
            f"Got keys: {sorted(mapping.keys())}"
        )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def _aadhaar_last_4(aadhaar: str) -> str:
    digits = "".join(ch for ch in aadhaar if ch.isdigit())
    return digits[-4:]


def _compute_overdue(scheme_thread: dict, charter_id: str, today: str) -> dict:
    _require(scheme_thread, ["scheme_id", "scheme_name", "application_id", "filed_at"], "scheme_thread")
    charter = get_charter(charter_id)
    charter_days = charter["stipulated_days_default"]
    days_elapsed = (_parse_date(today) - _parse_date(scheme_thread["filed_at"])).days
    days_overdue = max(0, days_elapsed - charter_days)
    if days_overdue == 0:
        raise ValueError(
            f"Application {scheme_thread['application_id']} is not yet overdue "
            f"({days_elapsed} days elapsed vs. {charter_days}-day charter timeline) — "
            "no basis for escalation."
        )
    return {
        "charter": charter,
        "charter_days": charter_days,
        "days_elapsed": days_elapsed,
        "days_overdue": days_overdue,
    }


def render_escalation_email(
    scheme_thread: dict,
    user_profile: dict,
    department: dict,
    charter_id: str,
    today: str,
) -> str:
    _require(user_profile, ["name", "aadhaar", "email", "phone"], "user_profile")
    _require(department, ["name", "grievance_officer_email"], "department")

    overdue = _compute_overdue(scheme_thread, charter_id, today)

    template = _env.get_template("escalation_email.j2")
    return template.render(
        app_id=scheme_thread["application_id"],
        grievance_officer_email=department["grievance_officer_email"],
        applicant_name=user_profile["name"],
        applicant_email=user_profile["email"],
        applicant_phone=user_profile["phone"],
        today=today,
        aadhaar_last_4=_aadhaar_last_4(user_profile["aadhaar"]),
        scheme_name=scheme_thread["scheme_name"],
        scheme_id=scheme_thread["scheme_id"],
        submission_date=scheme_thread["filed_at"],
        days_elapsed=overdue["days_elapsed"],
        charter_days=overdue["charter_days"],
        days_overdue=overdue["days_overdue"],
        department_name=department["name"],
    )


def render_rti_application(
    scheme_thread: dict,
    user_profile: dict,
    department: dict,
    charter_id: str,
    today: str,
    bpl_applicant: bool = False,
) -> str:
    _require(user_profile, ["name", "aadhaar", "email", "phone", "address", "city"], "user_profile")
    _require(department, ["name", "address"], "department")

    overdue = _compute_overdue(scheme_thread, charter_id, today)

    template = _env.get_template("rti_application.j2")
    return template.render(
        today=today,
        applicant_city=user_profile["city"],
        department_name=department["name"],
        department_address=department["address"],
        app_id=scheme_thread["application_id"],
        scheme_name=scheme_thread["scheme_name"],
        applicant_name=user_profile["name"],
        applicant_address=user_profile["address"],
        scheme_id=scheme_thread["scheme_id"],
        submission_date=scheme_thread["filed_at"],
        days_elapsed=overdue["days_elapsed"],
        charter_days=overdue["charter_days"],
        days_overdue=overdue["days_overdue"],
        bpl_applicant=bpl_applicant,
        applicant_phone=user_profile["phone"],
        applicant_email=user_profile["email"],
    )
