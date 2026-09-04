"""
Tests for backend/rti/renderer.py — three persona scenarios plus error cases.

The "every Section X(y) token appears in clauses.json" checks treat a
sub-clause citation (e.g. "Section 4(1)(b)(iv)") as backed by a clause
whose declared section is a prefix of it (e.g. clause section "4(1)(b)"),
since a sub-clause pinpoint reference is still grounded in that clause.
"""

import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from backend.mocks.fixtures import PRIYA_AADHAAR, RAJESH_AADHAAR, REKHA_AADHAAR
from backend.rti.renderer import (
    get_clause,
    load_clauses,
    render_escalation_email,
    render_rti_application,
)
from backend.state import make_scheme_thread

TODAY = date(2026, 1, 1)

SECTION_TOKEN_RE = re.compile(r"Section\s+(\d+(?:\(\w+\))+)")


def _known_sections():
    return {c["section"] for c in load_clauses()["clauses"]}


def _is_backed(token: str, known_sections: set) -> bool:
    if token in known_sections:
        return True
    return any(token.startswith(sec + "(") for sec in known_sections)


def _assert_all_sections_backed(text: str):
    known = _known_sections()
    tokens = SECTION_TOKEN_RE.findall(text)
    unbacked = [t for t in tokens if not _is_backed(t, known)]
    assert not unbacked, f"Unbacked section citations found in output: {unbacked}"


def _thread(scheme_id, scheme_name, application_id, filed_days_ago, charter_days):
    thread = make_scheme_thread(
        scheme_id=scheme_id,
        scheme_name=scheme_name,
        confidence=0.9,
        charter_deadline_days=charter_days,
    )
    thread["application_id"] = application_id
    thread["filed_at"] = (TODAY - timedelta(days=filed_days_ago)).isoformat()
    return thread


def test_escalation_email_rekha_education():
    thread = _thread("PM-VIDYALAXMI", "PM Vidyalaxmi Scheme", "APP-PM-VIDYALAXMI-TEST001", 60, 45)
    user_profile = {
        "name": "Rekha Murugan",
        "aadhaar": REKHA_AADHAAR,
        "email": "rekha.murugan@example.com",
        "phone": "+91-9000000001",
    }
    department = {
        "name": "Department of Higher Education, Tamil Nadu",
        "grievance_officer_email": "grievance.edu@tn.gov.in",
    }

    output = render_escalation_email(thread, user_profile, department, "TN-EDU-CHARTER", TODAY.isoformat())

    assert "Rekha Murugan" in output
    assert f"XXXX-XXXX-{REKHA_AADHAAR[-4:]}" in output
    assert thread["application_id"] in output
    assert "45 days" in output
    assert "Overdue By" in output and "15 days" in output

    assert "Section 6(1)" in output
    assert "Section 20(1)" in output
    _assert_all_sections_backed(output)


def test_rti_application_rajesh_agriculture():
    thread = _thread("PM-KISAN", "PM-KISAN", "APP-PM-KISAN-TEST002", 100, 60)
    user_profile = {
        "name": "Rajesh Kumar",
        "aadhaar": RAJESH_AADHAAR,
        "email": "rajesh.kumar@example.com",
        "phone": "+91-9000000002",
        "address": "Village Road, Thanjavur, Tamil Nadu",
        "city": "Thanjavur",
    }
    department = {
        "name": "Department of Agriculture and Farmers Welfare, Tamil Nadu",
        "address": "Chepauk, Chennai - 600005",
    }

    output = render_rti_application(
        thread, user_profile, department, "TN-AGRI-CHARTER", TODAY.isoformat(), bpl_applicant=False
    )

    for expected in [
        "Section 6(1)",
        "Section 4(1)(b)(iv)",
        "Section 7(1)",
        "Section 7(6)",
        "Section 19(1)",
        "Section 20(1)",
    ]:
        assert expected in output

    _assert_all_sections_backed(output)

    assert "Below Poverty Line" not in output
    assert "second proviso to Section 7(5)" not in output


def test_rti_application_priya_bpl_widow():
    thread = _thread("PM-VVY", "Pradhan Mantri Vaya Vandana Yojana", "APP-PM-VVY-TEST003", 120, 90)
    user_profile = {
        "name": "Priya Sundaram",
        "aadhaar": PRIYA_AADHAAR,
        "email": "priya.sundaram@example.com",
        "phone": "+91-9000000003",
        "address": "Amman Koil Street, Chennai, Tamil Nadu",
        "city": "Chennai",
    }
    department = {
        "name": "Department of Social Welfare and Women Empowerment, Tamil Nadu",
        "address": "Kuralagam, Chennai - 600108",
    }

    output = render_rti_application(
        thread, user_profile, department, "TN-SOCWEL-CHARTER", TODAY.isoformat(), bpl_applicant=True
    )

    assert "Below Poverty Line" in output
    assert "second proviso to Section 7(5)" in output


def test_raises_when_not_overdue():
    thread = _thread("PM-KISAN", "PM-KISAN", "APP-PM-KISAN-TEST004", 5, 60)
    user_profile = {
        "name": "Rajesh Kumar",
        "aadhaar": RAJESH_AADHAAR,
        "email": "rajesh.kumar@example.com",
        "phone": "+91-9000000002",
    }
    department = {
        "name": "Department of Agriculture and Farmers Welfare, Tamil Nadu",
        "grievance_officer_email": "grievance.agri@tn.gov.in",
    }

    with pytest.raises(ValueError):
        render_escalation_email(thread, user_profile, department, "TN-AGRI-CHARTER", TODAY.isoformat())


def test_raises_on_missing_clause():
    with pytest.raises(KeyError):
        get_clause("RTI-9999-FAKE")
