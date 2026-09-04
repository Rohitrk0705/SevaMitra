"""
backend/ingestion/retrieve.py

Query helper for the persisted "sevamithra_schemes" ChromaDB collection.
Used by the Discovery Agent (Rung 8) to semantically match a citizen's
situation against the scheme corpus.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

CHROMA_DB_DIR = str(Path(__file__).resolve().parent.parent / "chroma_db")
COLLECTION_NAME = "sevamithra_schemes"

_NORMALISED_SCHEME_KEYS = (
    "scheme_id",
    "name",
    "description",
    "department",
    "state",
    "category",
    "target_beneficiaries",
    "eligibility_notes",
    "required_documents",
    "citizen_charter_days",
    "income_max",
    "age_min",
    "age_max",
    "landholding_max_hectares",
    "gender",
    "official_source_url",
)

_client: Optional["chromadb.ClientAPI"] = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        embedding_function = embedding_functions.DefaultEmbeddingFunction()
        _collection = _client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function,
        )
    return _collection


def query_schemes(text: str, n_results: int = 5, where: Optional[dict] = None) -> list:
    """Semantically queries the scheme collection.

    Returns a list of dicts, each with every NormalisedScheme field
    (missing/omitted metadata keys default to None) plus a "distance" score.
    required_documents is deserialised from its stored JSON string back to
    a list.
    """
    collection = _get_collection()
    results = collection.query(
        query_texts=[text],
        n_results=n_results,
        where=where,
    )

    ids = results.get("ids", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for scheme_id, metadata, distance in zip(ids, metadatas, distances):
        record = {key: metadata.get(key) for key in _NORMALISED_SCHEME_KEYS}
        record["scheme_id"] = record["scheme_id"] or scheme_id

        raw_docs = metadata.get("required_documents")
        try:
            record["required_documents"] = json.loads(raw_docs) if raw_docs else []
        except (TypeError, json.JSONDecodeError):
            logger.warning("Could not deserialise required_documents for %s", scheme_id)
            record["required_documents"] = []

        record["distance"] = distance
        output.append(record)

    return output
