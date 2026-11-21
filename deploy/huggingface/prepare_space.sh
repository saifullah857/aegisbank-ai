#!/usr/bin/env bash
# Builds a clean ./hf_space folder (no venv / node_modules / .git / databases) ready to push to a Hugging Face Space.
# Usage (from the project root):   bash deploy/huggingface/prepare_space.sh
set -euo pipefail
OUT="${1:-hf_space}"
rm -rf "$OUT" && mkdir -p "$OUT"
tar --exclude='venv' --exclude='__pycache__' --exclude='*.db' --exclude='data' --exclude='tests' --exclude='artifacts' --exclude='.pytest_cache' --exclude='.ruff_cache' \
    --exclude='node_modules' --exclude='dist' -cf - backend frontend rag_documents | tar -xf - -C "$OUT"
cp deploy/huggingface/Dockerfile "$OUT/Dockerfile"
cp deploy/huggingface/README.md "$OUT/README.md"
printf 'backend/venv\n**/__pycache__\n**/node_modules\n*.db\n' > "$OUT/.dockerignore"
echo "Space folder ready: $OUT  ($(du -sh "$OUT" | cut -f1))"
echo "Next: cd $OUT && git init -b main && git remote add space https://huggingface.co/spaces/<USER>/<SPACE> && git add . && git commit -m 'Deploy' && git push space main"
