#!/usr/bin/env bash
set -euo pipefail

# Dump Neo4j database running in docker-compose service neo4j-db
# Usage: ./scripts/dumps/dump_neo4j.sh
# Output: dumps/neo4j/<timestamp>/neo4j.dump
# Note: Neo4j must be stopped before dumping (script handles this automatically)

DB_NAME=${NEO4J_DB:-neo4j}
CONTAINER=${NEO4J_CONTAINER:-neo4j-db}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="dumps/neo4j/${TIMESTAMP}"
DUMP_FILE="${DB_NAME}.dump"

mkdir -p "${OUT_DIR}"

echo "[+] Stopping Neo4j container"
docker compose stop "${CONTAINER}"

echo "[+] Starting container for dump (database remains stopped)"
docker compose start "${CONTAINER}"
sleep 2

echo "[+] Creating dump of database '${DB_NAME}'"
docker compose exec -T "${CONTAINER}" bash -c "mkdir -p /data/backups && neo4j-admin database dump ${DB_NAME} --to-path=/data/backups --overwrite-destination"

echo "[+] Copying dump file to host"
docker compose cp "${CONTAINER}:/data/backups/${DUMP_FILE}" "${OUT_DIR}/${DUMP_FILE}"

echo "[+] Restarting Neo4j"
docker compose restart "${CONTAINER}"

echo "[+] Dump complete: ${OUT_DIR}/${DUMP_FILE}"
echo ""
echo "Restore example:"
echo "  docker compose stop ${CONTAINER}"
echo "  docker compose start ${CONTAINER}"
echo "  docker compose exec -T ${CONTAINER} neo4j-admin database load ${DB_NAME} --from-path=/data/backups --overwrite-destination"
echo "  docker compose restart ${CONTAINER}"
