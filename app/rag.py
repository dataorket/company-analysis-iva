"""
RAG Retriever
Queries ChromaDB to find relevant document chunks for a given query.
"""

import chromadb
from app.config import CHROMA_PERSIST_DIR, COLLECTION_MENSCH, COLLECTION_TYSON

# Lazy-initialized client
_chroma_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


def retrieve_chunks(
    query: str,
    company: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve the most relevant document chunks for a query.

    Args:
        query:   The user's question.
        company: Collection name ("mensch_und_maschine" or "tyson_foods").
                 If None, searches both collections.
        top_k:   Number of chunks to return.

    Returns:
        List of dicts: [{text, source, company, score}, ...]
    """
    client = _get_client()
    results = []

    collections_to_search = []
    if company:
        collections_to_search.append(company)
    else:
        collections_to_search = [COLLECTION_MENSCH, COLLECTION_TYSON]

    for coll_name in collections_to_search:
        try:
            collection = client.get_collection(coll_name)
        except Exception:
            continue

        query_result = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()) if collection.count() > 0 else 1,
        )

        if query_result and query_result["documents"]:
            for i, doc in enumerate(query_result["documents"][0]):
                distance = query_result["distances"][0][i] if query_result.get("distances") else 0
                metadata = query_result["metadatas"][0][i] if query_result.get("metadatas") else {}
                results.append({
                    "text": doc,
                    "source": metadata.get("source", "unknown"),
                    "company": coll_name,
                    "score": 1 - distance,  # Convert distance to similarity
                })

    # Sort by relevance score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def get_collection_stats() -> dict:
    """Return document counts per collection. Used for health checks."""
    client = _get_client()
    stats = {}
    for name in [COLLECTION_MENSCH, COLLECTION_TYSON]:
        try:
            coll = client.get_collection(name)
            stats[name] = coll.count()
        except Exception:
            stats[name] = 0
    return stats
