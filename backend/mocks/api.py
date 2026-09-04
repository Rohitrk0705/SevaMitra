"""
Mock Indian government APIs. Simulates Aadhaar UIDAI, DigiLocker,
and generic scheme application status endpoints.

Run standalone: uvicorn backend.mocks.api:app --reload --port 8001
"""
from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone, timedelta
import uuid

from backend.mocks.models import (
    AadhaarVerifyRequest, AadhaarVerifyResponse,
    DigilockerDocument, DigilockerFetchResponse,
    ApplicationSubmitRequest, ApplicationSubmitResponse,
    ApplicationStatusResponse,
)
from backend.mocks.fixtures import (
    AADHAAR_RECORDS, DIGILOCKER_DOCUMENTS,
    SUBMITTED_APPLICATIONS, ALWAYS_PENDING_FOR_DEMO,
)


app = FastAPI(
    title="SevaMithra Mock Gov APIs",
    description="Simulates Aadhaar, DigiLocker, and application status endpoints",
    version="1.0.0",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Aadhaar UIDAI mock ----------

@app.post("/aadhaar/verify", response_model=AadhaarVerifyResponse)
def verify_aadhaar(req: AadhaarVerifyRequest) -> AadhaarVerifyResponse:
    record = AADHAAR_RECORDS.get(req.aadhaar_number)
    if record is None:
        return AadhaarVerifyResponse(
            aadhaar_number=req.aadhaar_number,
            status="not_found",
            verified_at=_now_iso(),
        )
    return AadhaarVerifyResponse(
        aadhaar_number=req.aadhaar_number,
        status=record["status"],
        name_on_record=record["name_on_record"],
        dob_on_record=record["dob_on_record"],
        verified_at=_now_iso(),
    )


# ---------- DigiLocker mock ----------

@app.get("/digilocker/documents/{aadhaar_number}", response_model=DigilockerFetchResponse)
def fetch_digilocker_documents(aadhaar_number: str) -> DigilockerFetchResponse:
    if aadhaar_number not in AADHAAR_RECORDS:
        raise HTTPException(status_code=404, detail=f"No DigiLocker vault found for Aadhaar {aadhaar_number}")
    docs = DIGILOCKER_DOCUMENTS.get(aadhaar_number, [])
    return DigilockerFetchResponse(
        aadhaar_number=aadhaar_number,
        documents=[DigilockerDocument(**d) for d in docs],
        fetched_at=_now_iso(),
    )


# ---------- Generic scheme application submit + status ----------

@app.post("/applications/submit", response_model=ApplicationSubmitResponse)
def submit_application(req: ApplicationSubmitRequest) -> ApplicationSubmitResponse:
    if req.aadhaar_number not in AADHAAR_RECORDS:
        raise HTTPException(status_code=400, detail="Invalid Aadhaar — user not in system")
    app_id = f"APP-{req.scheme_id}-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)
    expected_by = (now + timedelta(days=60)).date().isoformat()
    SUBMITTED_APPLICATIONS[app_id] = {
        "application_id": app_id,
        "scheme_id": req.scheme_id,
        "aadhaar_number": req.aadhaar_number,
        "status": "pending",
        "submitted_at": now.isoformat(),
        "last_updated_at": now.isoformat(),
        "documents_attached": req.documents_attached,
        "officer_notes": None,
    }
    return ApplicationSubmitResponse(
        application_id=app_id,
        scheme_id=req.scheme_id,
        status="submitted",
        submitted_at=now.isoformat(),
        expected_response_by=expected_by,
        tracking_url=f"http://localhost:8001/applications/status/{app_id}",
    )


@app.get("/applications/status/{application_id}", response_model=ApplicationStatusResponse)
def get_application_status(application_id: str) -> ApplicationStatusResponse:
    record = SUBMITTED_APPLICATIONS.get(application_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found")
    submitted_at = datetime.fromisoformat(record["submitted_at"])
    days_since = (datetime.now(timezone.utc) - submitted_at).days
    status = "pending" if ALWAYS_PENDING_FOR_DEMO else record["status"]
    return ApplicationStatusResponse(
        application_id=application_id,
        scheme_id=record["scheme_id"],
        status=status,
        submitted_at=record["submitted_at"],
        last_updated_at=record["last_updated_at"],
        days_since_submission=days_since,
        officer_notes=record["officer_notes"],
    )


# ---------- Health check ----------

@app.get("/health")
def health():
    return {"status": "ok", "service": "sevamithra-mock-gov-apis", "timestamp": _now_iso()}
