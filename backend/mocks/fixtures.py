"""
Fixtures for demo personas. Every mock endpoint reads from here.
Rekha = 18yo student, farmer's daughter, Tamil Nadu — scholarship persona
Rajesh = 45yo farmer with 2 acres, Tamil Nadu — agriculture scheme persona
Priya = wildcard: 62yo widow, Tamil Nadu — pension/social security persona

Rung 9: Rajesh carries two conflicting land_records entries (2019 vs 2023
survey) to exercise Validator's LLM conflict-resolution path, plus a
chitta_adangal document standing in for a missing land_patta_documents to
exercise fallback-document recovery. Rekha's income_certificate was
flipped from expired to valid (Rung 9 Task 1 calls for "all present and
current" for her persona). Priya gained widow_certificate and
bpl_certificate to match her Rung 9 persona description.
"""

REKHA_AADHAAR = "234567890123"
RAJESH_AADHAAR = "345678901234"
PRIYA_AADHAAR = "456789012345"


AADHAAR_RECORDS = {
    REKHA_AADHAAR: {
        "name_on_record": "Rekha Murugan",
        "dob_on_record": "2008-03-15",
        "status": "verified",
    },
    RAJESH_AADHAAR: {
        "name_on_record": "Rajesh Kumar",
        "dob_on_record": "1981-07-22",
        "status": "verified",
    },
    PRIYA_AADHAAR: {
        "name_on_record": "Priya Sundaram",
        "dob_on_record": "1964-11-05",
        "status": "verified",
    },
}


DIGILOCKER_DOCUMENTS = {
    REKHA_AADHAAR: [
        {
            "document_type": "aadhaar_card",
            "document_id": "AAD-234567890123",
            "issued_by": "UIDAI",
            "issued_at": "2015-06-10",
            "valid_until": None,
            "status": "valid",
            "metadata": {"name": "Rekha Murugan", "dob": "2008-03-15"},
        },
        {
            "document_type": "income_certificate",
            "document_id": "TN-INC-2025-478291",
            "issued_by": "Tahsildar, Coimbatore",
            "issued_at": "2025-04-15",
            "valid_until": "2027-04-14",
            "status": "valid",
            "metadata": {"annual_family_income_inr": 84000},
        },
        {
            "document_type": "educational_certificates",
            "document_id": "TN-SSLC-2024-9982",
            "issued_by": "TN Board of Secondary Education",
            "issued_at": "2024-05-20",
            "valid_until": None,
            "status": "valid",
            "metadata": {"class": "10", "marks_percentage": 87.5},
        },
        {
            "document_type": "bank_passbook",
            "document_id": "BANK-SBI-33445566",
            "issued_by": "State Bank of India",
            "issued_at": "2023-09-01",
            "valid_until": None,
            "status": "valid",
            "metadata": {"ifsc": "SBIN0001234", "account_type": "savings"},
        },
        {
            "document_type": "caste_certificate",
            "document_id": "TN-CST-2020-11223",
            "issued_by": "Tahsildar, Coimbatore",
            "issued_at": "2020-08-12",
            "valid_until": None,
            "status": "valid",
            "metadata": {"category": "obc"},
        },
    ],
    RAJESH_AADHAAR: [
        {
            "document_type": "aadhaar_card",
            "document_id": "AAD-345678901234",
            "issued_by": "UIDAI",
            "issued_at": "2013-02-14",
            "valid_until": None,
            "status": "valid",
            "metadata": {"name": "Rajesh Kumar", "dob": "1981-07-22"},
        },
        {
            "document_type": "land_records",
            "document_id": "TN-LAND-THJ-2019-7788",
            "issued_by": "Revenue Dept, Thanjavur",
            "issued_at": "2019-06-08",
            "valid_until": None,
            "status": "valid",
            "metadata": {"land_area_hectares": 0.8, "district": "Thanjavur", "survey_number": "142/3B"},
        },
        {
            # Conflicting resurvey record: same person, same document_type,
            # different land area — exercises Validator's LLM conflict
            # resolution path (Rung 9).
            "document_type": "land_records",
            "document_id": "TN-LAND-THJ-2023-9910",
            "issued_by": "Revenue Dept, Thanjavur",
            "issued_at": "2023-11-02",
            "valid_until": None,
            "status": "valid",
            "metadata": {"land_area_hectares": 0.97, "district": "Thanjavur", "survey_number": "142/3B-R"},
        },
        {
            # Stands in for a missing "land_patta_documents" — exercises
            # Validator's fallback-document recovery path (Rung 9).
            "document_type": "chitta_adangal",
            "document_id": "TN-CHAD-THJ-2022-3345",
            "issued_by": "Village Administrative Officer, Thanjavur",
            "issued_at": "2022-03-10",
            "valid_until": None,
            "status": "valid",
            "metadata": {"land_area_hectares": 0.8, "district": "Thanjavur", "survey_number": "142/3B"},
        },
        {
            "document_type": "bank_passbook",
            "document_id": "BANK-IOB-99887766",
            "issued_by": "Indian Overseas Bank",
            "issued_at": "2020-01-15",
            "valid_until": None,
            "status": "valid",
            "metadata": {"ifsc": "IOBA0001100", "account_type": "savings"},
        },
        {
            "document_type": "income_certificate",
            "document_id": "TN-INC-2024-556677",
            "issued_by": "Tahsildar, Thanjavur",
            "issued_at": "2024-01-20",
            "valid_until": "2025-01-19",
            "status": "valid",
            "metadata": {"annual_family_income_inr": 145000},
        },
    ],
    PRIYA_AADHAAR: [
        {
            "document_type": "aadhaar_card",
            "document_id": "AAD-456789012345",
            "issued_by": "UIDAI",
            "issued_at": "2014-05-19",
            "valid_until": None,
            "status": "valid",
            "metadata": {"name": "Priya Sundaram", "dob": "1964-11-05"},
        },
        {
            "document_type": "bank_passbook",
            "document_id": "BANK-CANARA-11223344",
            "issued_by": "Canara Bank",
            "issued_at": "2018-11-01",
            "valid_until": None,
            "status": "valid",
            "metadata": {"ifsc": "CNRB0001234", "account_type": "savings"},
        },
        {
            "document_type": "widow_certificate",
            "document_id": "TN-WID-2015-2234",
            "issued_by": "Tahsildar, Chennai",
            "issued_at": "2015-08-20",
            "valid_until": None,
            "status": "valid",
            "metadata": {},
        },
        {
            "document_type": "bpl_certificate",
            "document_id": "TN-BPL-2020-8871",
            "issued_by": "Revenue Department, Chennai",
            "issued_at": "2020-02-14",
            "valid_until": None,
            "status": "valid",
            "metadata": {},
        },
    ],
}


# Applications submitted during a session — mutable, in-memory
# Keyed by application_id. Reset on server restart.
SUBMITTED_APPLICATIONS: dict = {}


# Deterministic per-persona application status outcomes (Rung 9, replaces
# the old ALWAYS_PENDING_FOR_DEMO global flag, which would have collided
# with Rung 10's Monitor logic by pending every application uniformly).
#
# Rekha's applications stay "pending" indefinitely — this is what
# triggers the Rung 10 Monitor -> RTI escalation demo path. Rajesh's and
# Priya's applications report "approved" once checked, regardless of
# which Validator path (clean / conflict-resolved / fallback-recovered)
# got them filed — the divergence is in *how* Validator got them there,
# not in the final status.
PERSONA_STATUS_OUTCOME = {
    REKHA_AADHAAR: "pending",
    RAJESH_AADHAAR: "approved",
    PRIYA_AADHAAR: "approved",
}
