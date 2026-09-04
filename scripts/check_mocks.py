"""Test all mock endpoints end-to-end via FastAPI TestClient."""
from fastapi.testclient import TestClient
from backend.mocks.api import app
from backend.mocks.fixtures import REKHA_AADHAAR, RAJESH_AADHAAR

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("✓ /health")


def test_aadhaar_verify_known():
    r = client.post("/aadhaar/verify", json={"aadhaar_number": REKHA_AADHAAR})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "verified"
    assert body["name_on_record"] == "Rekha Murugan"
    print(f"✓ /aadhaar/verify (Rekha): {body['status']}")


def test_aadhaar_verify_unknown():
    r = client.post("/aadhaar/verify", json={"aadhaar_number": "999999999999"})
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"
    print("✓ /aadhaar/verify (unknown): not_found")


def test_digilocker_rekha_has_expired_income_cert():
    r = client.get(f"/digilocker/documents/{REKHA_AADHAAR}")
    assert r.status_code == 200
    docs = r.json()["documents"]
    income_cert = next(d for d in docs if d["document_type"] == "income_certificate")
    assert income_cert["status"] == "expired"
    print(f"✓ /digilocker (Rekha): found expired income cert issued {income_cert['issued_at']}")


def test_digilocker_rajesh_has_land_records():
    r = client.get(f"/digilocker/documents/{RAJESH_AADHAAR}")
    assert r.status_code == 200
    docs = r.json()["documents"]
    land = next(d for d in docs if d["document_type"] == "land_records")
    assert land["status"] == "valid"
    assert land["metadata"]["land_area_hectares"] == 0.8
    print(f"✓ /digilocker (Rajesh): valid land record, {land['metadata']['land_area_hectares']} hectares")


def test_application_submit_and_status():
    submit = client.post("/applications/submit", json={
        "aadhaar_number": RAJESH_AADHAAR,
        "scheme_id": "IN-AGRI-002",
        "documents_attached": ["aadhaar_card", "land_records", "bank_passbook"],
        "applicant_profile": {"name": "Rajesh Kumar", "land_hectares": 0.8},
    })
    assert submit.status_code == 200
    app_id = submit.json()["application_id"]
    print(f"✓ /applications/submit: {app_id}")

    status = client.get(f"/applications/status/{app_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "pending"  # ALWAYS_PENDING_FOR_DEMO
    print(f"✓ /applications/status: {body['status']} (this pending state is what triggers RTI escalation)")


if __name__ == "__main__":
    test_health()
    test_aadhaar_verify_known()
    test_aadhaar_verify_unknown()
    test_digilocker_rekha_has_expired_income_cert()
    test_digilocker_rajesh_has_land_records()
    test_application_submit_and_status()
    print("\nAll mock endpoint tests passed.")
