"""
pytest suite for backend/ingestion. Ingests the full corpus once per test
session (idempotent — delete + recreate) so the query tests run against
real, freshly built data.

Run: pytest backend/ingestion/tests/ -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest

from backend.ingestion.ingest import SCHEME_DATA_DIR, run_ingestion
from backend.ingestion.normalise import normalise_scheme
from backend.ingestion.retrieve import query_schemes


@pytest.fixture(scope="session", autouse=True)
def ingested_collection():
    run_ingestion()


def test_normalise_handles_all_batches():
    batch_files = sorted(Path(SCHEME_DATA_DIR).glob("schemes_batch_*.json"))
    assert len(batch_files) == 7, f"expected 7 batch files, found {len(batch_files)}"

    for batch_file in batch_files:
        with open(batch_file) as f:
            raw_schemes = json.load(f)
        first = raw_schemes[0]
        normalised = normalise_scheme(first, batch_file.stem)
        assert normalised["scheme_id"] == first["scheme_id"]
        assert normalised["state"] in ("Central", "Tamil Nadu")


def test_ingest_and_query_farmer():
    results = query_schemes("farmer with 2 acres growing paddy", n_results=5)
    assert len(results) > 0
    categories = [r["category"] for r in results]
    assert "agriculture" in categories, f"expected an agriculture result, got {categories}"


def test_ingest_and_query_scholarship():
    results = query_schemes("girl child scholarship for college", n_results=5)
    assert len(results) > 0
    categories = [r["category"] for r in results]
    assert "education" in categories, f"expected an education result, got {categories}"


def test_ingest_and_query_pension():
    results = query_schemes("widow monthly pension", n_results=5)
    assert len(results) > 0
    categories = [r["category"] for r in results]
    assert "social_welfare" in categories, f"expected a social_welfare result, got {categories}"


def test_metadata_filter_state():
    results = query_schemes(
        "financial assistance scheme",
        n_results=10,
        where={"state": "Tamil Nadu"},
    )
    assert len(results) > 0
    states = {r["state"] for r in results}
    assert states == {"Tamil Nadu"}, f"expected only Tamil Nadu results, got {states}"
