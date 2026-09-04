"""
backend/ingestion/ingest.py

Reads all schemes_batch_*.json files, normalises every scheme, embeds each
scheme's semantic text, and persists to a local ChromaDB collection.

Run as: python -m backend.ingestion.ingest
"""

import json
import os
import time
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from backend.ingestion.normalise import build_embedding_text, normalise_scheme

SCHEME_DATA_DIR = os.getenv("SCHEME_DATA_DIR", os.path.expanduser("~/Desktop/hackwave/data"))
CHROMA_DB_DIR = str(Path(__file__).resolve().parent.parent / "chroma_db")
COLLECTION_NAME = "sevamithra_schemes"


def _load_batches(data_dir: str) -> list:
    batch_files = sorted(Path(data_dir).glob("schemes_batch_*.json"))
    if not batch_files:
        raise FileNotFoundError(f"No schemes_batch_*.json files found in {data_dir}")
    return batch_files


def run_ingestion() -> int:
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    embedding_function = embedding_functions.DefaultEmbeddingFunction()

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
    )

    total = 0
    for batch_file in _load_batches(SCHEME_DATA_DIR):
        batch_name = batch_file.stem
        with open(batch_file) as f:
            raw_schemes = json.load(f)

        ids, documents, metadatas = [], [], []
        for raw in raw_schemes:
            scheme = normalise_scheme(raw, batch_name)
            document = build_embedding_text(scheme)

            metadata = dict(scheme)
            metadata["required_documents"] = json.dumps(metadata["required_documents"])
            metadata = {k: v for k, v in metadata.items() if v is not None}

            ids.append(scheme["scheme_id"])
            documents.append(document)
            metadatas.append(metadata)

        start = time.monotonic()
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        elapsed_s = time.monotonic() - start

        print(f"{batch_name}: {len(raw_schemes)} schemes embedded in {elapsed_s:.2f}s")
        total += len(raw_schemes)

    print(f"Total: {total} schemes")
    print(f"Ingestion complete: {total} schemes in collection {COLLECTION_NAME}")
    return total


if __name__ == "__main__":
    run_ingestion()
