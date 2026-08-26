"""Query Pinecone for evidence relevant to a compliance question."""

from app.rag.ingest import embed_texts, get_pinecone_index


def retrieve_evidence(query: str, top_k: int = 3) -> list[dict]:
    pc, index = get_pinecone_index()
    query_vector = embed_texts(pc, [query], input_type="query")[0]
    results = index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    return [
        {
            "source": match["metadata"]["source"],
            "text": match["metadata"]["text"],
            "score": match["score"],
        }
        for match in results["matches"]
    ]
