"""
Fixtures for demo personas. Every mock endpoint reads from here.
Rekha = 18yo student, farmer's daughter, Tamil Nadu — scholarship persona
Rajesh = 45yo farmer with 2 acres, Tamil Nadu — agriculture scheme persona
Priya = wildcard: 62yo widow, Tamil Nadu — pension/social security persona
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
            "document_id": "TN-INC-2022-478291",
            "issued_by": "Tahsildar, Coimbatore",
            "issued_at": "2022-04-15",
            "valid_until": "2023-04-14",
            "status": "expired",
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
    ],
}


# Applications submitted during a session — mutable, in-memory
# Keyed by application_id. Reset on server restart.
SUBMITTED_APPLICATIONS: dict = {}


# Demo behavior toggle:
# When true, every application_id ever queried returns status="pending"
# regardless of days elapsed. This is what triggers the RTI escalation
# demo — deadline passes, status still pending, agent escalates.
ALWAYS_PENDING_FOR_DEMO = True
