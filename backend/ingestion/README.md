# backend/ingestion — ChromaDB scheme ingestion

## What it does

Reads the 7 `schemes_batch_*.json` files (253 government welfare schemes:
50 central + 203 Tamil Nadu, spanning agriculture, education, social
welfare, healthcare, and employment/MSME), normalises every scheme to one
schema (`NormalisedScheme`), embeds each scheme's semantic text with
ChromaDB's default embedding function, and persists the result to a local,
on-disk ChromaDB collection (`sevamithra_schemes`) at `backend/chroma_db/`.

This is a standalone library — it does not call LangGraph, FastAPI, or any
other backend module. It exists purely to make the scheme corpus
semantically queryable for the Discovery Agent (Rung 8), which is not built
here.

## How to run

```bash
python -m backend.ingestion.ingest
```

Deletes and recreates the `sevamithra_schemes` collection each run, so it's
safe to re-run — cheap for a corpus this size (well under a minute).

Reads from `SCHEME_DATA_DIR` (default: `~/Desktop/hackwave/data`). Override
with an env var if the batch files live elsewhere:

```bash
SCHEME_DATA_DIR=/path/to/data python -m backend.ingestion.ingest
```

To query:

```python
from backend.ingestion.retrieve import query_schemes

results = query_schemes("farmer with 2 acres growing paddy", n_results=5)
for r in results:
    print(r["scheme_id"], r["name"], r["category"], r["distance"])
```

`retrieve.py` opens its own `PersistentClient` against the same
`backend/chroma_db/` directory — it does not need ingestion to have run in
the same process. Run ingestion once, then query from any later process.

## NormalisedScheme shape

| Field | Type | Notes |
|---|---|---|
| `scheme_id` | `str` | e.g. `"IN-SOCL-001"`, `"TN-AGRI-015"` |
| `name` | `str` | |
| `description` | `str` | from `short_description`, falls back to `benefit_description` |
| `department` | `str` | from `sponsoring_department` |
| `state` | `str` | `"Central"` for batch 01, `"Tamil Nadu"` for batches 02-07 |
| `category` | `str` | one of `agriculture`, `education`, `social_welfare`, `healthcare`, `employment_msme`, `other` — resolved from the raw multi-tag `category` list by priority (see below) |
| `target_beneficiaries` | `str` | **derived**, not a source field — see below |
| `eligibility_notes` | `str` | |
| `required_documents` | `list[str]` | JSON-encoded in Chroma metadata, decoded back to a list by `retrieve.py` |
| `citizen_charter_days` | `int \| None` | |
| `income_max` | `int \| None` | from `eligibility_structured.max_annual_income_inr` |
| `age_min` / `age_max` | `int \| None` | |
| `landholding_max_hectares` | `float \| None` | |
| `gender` | `str \| None` | |
| `official_source_url` | `str` | |

**Category resolution.** The raw data tags each scheme with multiple
free-text categories (e.g. PM-KISAN is tagged both `social_security` and
`agriculture`). Since `NormalisedScheme.category` is a single enum value,
tags are resolved by priority: **agriculture > education > healthcare >
employment_msme > social_welfare > other**. This ordering was chosen by
inspecting real records — a scheme fundamentally about farmer income
support should classify as agriculture even if it's also tagged with a
generic welfare label.

**target_beneficiaries** has no direct source field in the raw JSON. It's
derived from `eligibility_structured.occupation` plus a small number of
category tags mapped to beneficiary phrases (`women_empowerment` → `women`,
`elderly_welfare` → `elderly persons`, etc.), falling back to `"general
public"` if nothing matches. This is a heuristic for embedding text
quality, not a verified field — do not treat it as authoritative.

## How to add a new batch

1. Drop `schemes_batch_NN_<name>.json` into `SCHEME_DATA_DIR`, matching the
   existing flat schema (see any current batch file for the field list).
2. If the new batch isn't Tamil Nadu or the existing central batch, check
   the `state` assignment in `normalise_scheme()` (`backend/ingestion/normalise.py`)
   — it currently hardcodes `"Central"` for batch 01 and `"Tamil Nadu"` for
   everything else.
3. If the new batch introduces category tags not covered by the existing
   tag sets (`_AGRICULTURE_TAGS`, `_EDUCATION_TAGS`, etc. in
   `normalise.py`), add them to the appropriate set — otherwise those
   schemes fall into `"other"`.
4. Re-run `python -m backend.ingestion.ingest` (idempotent — deletes and
   rebuilds the whole collection).

## First-run note

The first ingestion run downloads ChromaDB's default embedding model
(`all-MiniLM-L6-v2`, ONNX build, ~80MB) — needs an internet connection
once. Subsequent runs use the cached model (`~/.cache/chroma/onnx_models/`)
and work offline.
