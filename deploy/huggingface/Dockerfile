# Hugging Face Space (Docker SDK): ONE container = FastAPI + the built React app + SQLite. Listens on 7860.
# Build context = the Space repo root (created by deploy/huggingface/prepare_space.sh).
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# Spaces run the container as UID 1000, so own everything as that user.
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user backend/requirements.txt .
RUN pip install -r requirements.txt
COPY --chown=user backend/ ./
COPY --chown=user rag_documents/ ./rag_documents/
COPY --from=web --chown=user /web/dist ./frontend_dist
RUN mkdir -p /home/user/app/data && chown -R user:user /home/user/app
USER user

ENV ENVIRONMENT=production \
    PORT=7860 \
    DATABASE_URL=sqlite:////home/user/app/data/aegis.db \
    RAG_DOCUMENTS_DIR=/home/user/app/rag_documents \
    CHROMA_PERSIST_DIR=/home/user/app/data/chroma \
    ML_MODEL_PATH=/home/user/app/data/isolation_forest.joblib \
    RAG_EMBEDDER_PATH=/home/user/app/data/tfidf_embedder.joblib \
    FRONTEND_DIST=/home/user/app/frontend_dist \
    ALLOW_IFRAME=true \
    FORWARDED_ALLOW_IPS=* \
    SEED_ON_START=true SEED_CUSTOMERS=300 SEED_TXNS=3000 \
    WEB_CONCURRENCY=1
# Secrets (JWT_SECRET, optional GROQ_API_KEY, CORS_ORIGINS) are NOT baked in - add them under Space > Settings > Secrets.
EXPOSE 7860
CMD ["sh", "scripts/start.sh", "all"]
