#!/usr/bin/env bash
set -euo pipefail

export POETRY_VIRTUALENVS_CREATE=false
export POETRY_VIRTUALENVS_IN_PROJECT=false
PYTHON_BIN="python"

echo "[start] Backend initialization starting..."

# Optional: skip migrations if MIGRATE_ON_START != true
if [ "${MIGRATE_ON_START:-true}" != "true" ]; then
  echo "[start] MIGRATE_ON_START is not 'true' – skipping migrations."
  exec "${PYTHON_BIN}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-access-log
fi

# Wait for MongoDB availability
echo "[wait] Waiting for MongoDB to be ready..."
python - <<'PY'
import time
from pymongo import MongoClient
from app.config import get_settings
settings = get_settings()
for attempt in range(30):
    try:
        MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=3000).admin.command('ping')
        print(f"[wait] ✓ MongoDB ready after {attempt+1} attempt(s).")
        break
    except Exception as e:
        if attempt == 29:
            print(f"[wait] ✗ MongoDB failed to connect after 30 attempts: {e}")
            raise
        print(f"[wait] MongoDB not ready (attempt {attempt+1}/30), retrying...")
        time.sleep(3)
PY

# Wait for Neo4j availability
echo "[wait] Waiting for Neo4j to be ready..."
python - <<'PY'
import time
from neo4j import GraphDatabase
from app.config import get_settings
settings = get_settings()
for attempt in range(30):
    try:
        with GraphDatabase.driver(settings.neo4j_url, auth=(settings.neo4j_user, settings.neo4j_password)) as drv:
            drv.verify_connectivity()
        print(f"[wait] ✓ Neo4j ready after {attempt+1} attempt(s).")
        break
    except Exception as e:
        if attempt == 29:
            print(f"[wait] ✗ Neo4j failed to connect after 30 attempts: {e}")
            raise
        print(f"[wait] Neo4j not ready (attempt {attempt+1}/30), retrying...")
        time.sleep(3)
PY

# Run migrations (idempotent)
echo "[migrate] Running MongoDB migration..."
"${PYTHON_BIN}" scripts/migrate_to_mongodb.py

echo "[migrate] Running Neo4j migration..."
"${PYTHON_BIN}" scripts/migrate_to_neo4j.py

echo "[start] Launching API server..."
exec "${PYTHON_BIN}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-access-log
