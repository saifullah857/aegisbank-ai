# Build context is the repository root:  docker build -f backend/Dockerfile .
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ /app/
COPY rag_documents/ /app/rag_documents/

# Runtime artifacts (Chroma index, ML model, TF-IDF embedder) live in /app/data — mount a volume to persist them.
ENV RAG_DOCUMENTS_DIR=/app/rag_documents \
    CHROMA_PERSIST_DIR=/app/data/chroma \
    ML_MODEL_PATH=/app/data/isolation_forest.joblib \
    RAG_EMBEDDER_PATH=/app/data/tfidf_embedder.joblib
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data && chown -R app:app /app && chmod +x /app/scripts/start.sh
USER 10001

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status==200 else 1)"
CMD ["/app/scripts/start.sh", "all"]
