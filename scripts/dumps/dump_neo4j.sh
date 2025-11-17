#!/usr/bin/env bash
set -euo pipefail

# Dump Neo4j database running in docker-compose service neo4j-db
# Output: dumps/neo4j/<timestamp>/neo4j.dump
# Uses neo4j-admin database dump (Neo4j 5.x)

DB_NAME=${NEO4J_DB:-neo4j}
CONTAINER=${NEO4J_CONTAINER:-neo4j-db}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="dumps/neo4j/${TIMESTAMP}"
mkdir -p "${OUT_DIR}"

echo "[+] Creating Neo4j dump for database '${DB_NAME}'"
# Run dump inside container to /data/backups then copy out
# Ensure backups dir exists
docker compose exec -T "${CONTAINER}" bash -c "mkdir -p /data/backups && neo4j-admin database dump ${DB_NAME} --to=/data/backups --overwrite"

echo "[+] Copying dump file to host"
DUMP_FILE="${DB_NAME}.dump"
docker compose cp "${CONTAINER}:/data/backups/${DUMP_FILE}" "${OUT_DIR}/${DUMP_FILE}"

echo "[+] Dump complete: ${OUT_DIR}/${DUMP_FILE}"

echo "Restore example (will overwrite existing database):"
echo "  docker compose exec -T ${CONTAINER} neo4j-admin database load ${DB_NAME} --from-path=/data/backups --overwrite-destination"
