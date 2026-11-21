"""Policy retrieval: TF-IDF vectors (fit on the policy corpus, no model download needed) stored in ChromaDB.
retrieve() returns [] when the index hasn't been built, so callers degrade gracefully."""
from pathlib import Path

import chromadb
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import get_settings
from app.rag.chunking import load_all

COLLECTION = "banking_policies"
_vectorizer = None
_collection = None


def embedder_path() -> Path:
    p = get_settings().RAG_EMBEDDER_PATH
    return Path(p) if p else Path(__file__).resolve().parent / "artifacts" / "tfidf_embedder.joblib"


def _client():
    path = Path(get_settings().CHROMA_PERSIST_DIR)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def reset_cache() -> None:
    global _vectorizer, _collection
    _vectorizer = _collection = None


def ingest() -> int:
    """(Re)build the vector index from rag_documents/. Idempotent. Returns the number of chunks indexed."""
    chunks = load_all()
    if not chunks:
        raise RuntimeError("No policy documents found")
    vec = TfidfVectorizer(max_features=512, stop_words="english", ngram_range=(1, 2)).fit([c.embedding_text for c in chunks])
    embedder_path().parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(vec, embedder_path())
    client = _client()
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    col.add(ids=[c.chunk_id for c in chunks], embeddings=vec.transform([c.embedding_text for c in chunks]).toarray().tolist(),
            documents=[c.content for c in chunks],
            metadatas=[{"document": c.document_title, "policy_id": c.policy_id, "slug": c.slug, "section": c.section} for c in chunks])
    reset_cache()
    return len(chunks)


def _load():
    global _vectorizer, _collection
    if _vectorizer is None or _collection is None:
        if not embedder_path().exists():
            return None
        try:
            _vectorizer = joblib.load(embedder_path())
            _collection = _client().get_collection(COLLECTION)
        except Exception:
            _vectorizer = _collection = None
            return None
    return _vectorizer, _collection


def is_available() -> bool:
    return _load() is not None


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    loaded = _load()
    if loaded is None:
        return []
    vec, col = loaded
    res = col.query(query_embeddings=vec.transform([query]).toarray().tolist(), n_results=top_k)
    out = []
    for meta, doc, dist in zip(res["metadatas"][0], res["documents"][0], res["distances"][0]):
        out.append({"document": meta["document"], "policy_id": meta["policy_id"], "slug": meta["slug"], "section": meta["section"],
                    "content": doc, "score": round(max(0.0, 1.0 - dist / 2), 4)})
    return out


if __name__ == "__main__":
    print(f"indexed {ingest()} policy chunks")
