#!/bin/sh
# Container entrypoint.   start.sh [all|init|serve]
#   init  : migrate + seed synthetic data + train the ML model   (run once — Kubernetes Job)
#   serve : prepare local artifacts (ML model if missing, policy index) and run the API (Kubernetes Deployment)
#   all   : init + serve (Docker Compose, single backend)
set -e
MODE="${1:-all}"
MODEL="${ML_MODEL_PATH:-app/ml/artifacts/isolation_forest.joblib}"

if [ "$MODE" = "all" ] || [ "$MODE" = "init" ]; then
  echo "[aegis] applying migrations"
  alembic upgrade head
  if [ "${SEED_ON_START:-true}" = "true" ]; then
    echo "[aegis] seeding synthetic data (skipped if already present)"
    python -m app.db.seed
  fi
fi
[ "$MODE" = "init" ] && { echo "[aegis] init complete"; exit 0; }

if [ ! -f "$MODEL" ]; then
  echo "[aegis] training anomaly model from stored transactions"
  python -m app.ml.train || echo "[aegis] WARNING: model training failed — scoring will use the rule engine only"
fi
echo "[aegis] indexing policy documents"
python -m app.rag.policy_service || echo "[aegis] WARNING: policy index unavailable — investigations will mark RAG unavailable"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
