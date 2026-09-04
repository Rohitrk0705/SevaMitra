"""Pydantic request/response models for mock government APIs."""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class AadhaarVerifyRequest(BaseModel):
    aadhaar_number: str = Field(..., pattern=r"^\d{12}$", description="12-digit Aadhaar number")


class AadhaarVerifyResponse(BaseModel):
    aadhaar_number: str
    status: Literal["verified", "not_found", "mismatch"]
    name_on_record: Optional[str] = None
    dob_on_record: Optional[str] = None  # YYYY-MM-DD
    verified_at: str  # ISO timestamp


class DigilockerDocument(BaseModel):
    document_type: str  # e.g. "aadhaar_card", "income_certificate"
    document_id: str
    issued_by: str
    issued_at: str  # YYYY-MM-DD
    valid_until: Optional[str]  # YYYY-MM-DD, null if perpetual
    status: Literal["valid", "expired", "revoked"]
    metadata: dict  # scheme-relevant fields (income amount, land area, etc.)


class DigilockerFetchResponse(BaseModel):
    aadhaar_number: str
    documents: list[DigilockerDocument]
    fetched_at: str


class ApplicationSubmitRequest(BaseModel):
    aadhaar_number: str
    scheme_id: str
    documents_attached: list[str]  # document_type values
    applicant_profile: dict


class ApplicationSubmitResponse(BaseModel):
    application_id: str
    scheme_id: str
    status: Literal["submitted", "rejected_invalid"]
    submitted_at: str
    expected_response_by: str  # ISO date
    tracking_url: str


class ApplicationStatusResponse(BaseModel):
    application_id: str
    scheme_id: str
    status: Literal["pending", "under_review", "approved", "rejected", "info_requested"]
    submitted_at: str
    last_updated_at: str
    days_since_submission: int
    officer_notes: Optional[str] = None
