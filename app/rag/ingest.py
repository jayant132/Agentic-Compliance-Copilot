"""
Document ingestion pipeline: chunk -> embed -> upsert into Pinecone.
Run standalone with: python -m app.rag.ingest
"""

import glob
import os
import re

from pinecone import Pinecone, ServerlessSpec

from app.config import settings

EMBED_MODEL = "multilingual-e5-large"
EMBED_DIM = 1024

# Cached at module load, not per call. Originally get_pinecone_index()
# created a new Pinecone client and called list_indexes() on every
# single retrieval - a full network round-trip just to check an index
# that already exists. Measured impact: this accounted for most of the
# ~9s average RETRIEVE latency seen in evals/run_eval_extended.py.
_pc = None
_index = None


def get_pinecone_index():
    global _pc, _index
    if _pc is not None and _index is not None:
        return _pc, _index

    _pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = [i["name"] for i in _pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        _pc.create_index(
            name=settings.pinecone_index_name,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    _index = _pc.Index(settings.pinecone_index_name)
    return _pc, _index


def chunk_by_sections(text: str) -> list[str]:
    """Split a markdown doc on '## ' boundaries - each section is one
    citable policy requirement, instead of an arbitrary word window."""
    sections = re.split(r"\n(?=## )", text)
    return [s.strip() for s in sections if s.strip()]


def embed_texts(pc: Pinecone, texts: list[str], input_type: str) -> list[list[float]]:
    resp = pc.inference.embed(
        model=EMBED_MODEL,
        inputs=texts,
        parameters={"input_type": input_type, "truncate": "END"},
    )
    return [r["values"] for r in resp]


def ingest_documents(data_dir: str = "data") -> None:
    pc, index = get_pinecone_index()
    vectors = []

    for filepath in glob.glob(os.path.join(data_dir, "*.md")):
        filename = os.path.basename(filepath)
        text = open(filepath, encoding="utf-8").read()
        chunks = chunk_by_sections(text)
        embeddings = embed_texts(pc, chunks, input_type="passage")

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"{filename}-{i}",
                "values": emb,
                "metadata": {"source": filename, "text": chunk},
            })

    index.upsert(vectors=vectors)
    print(f"Ingested {len(vectors)} chunks from {len(glob.glob(os.path.join(data_dir, '*.md')))} documents.")


if __name__ == "__main__":
    ingest_documents()
