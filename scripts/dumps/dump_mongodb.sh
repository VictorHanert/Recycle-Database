#!/usr/bin/env bash
set -euo pipefail

# Dump MongoDB database running in docker-compose service mongo-db
# Usage command: ./scripts/dumps/dump_mongodb.sh
# Output: dumps/mongodb/<timestamp>/
# Requires mongodump available in the container (official mongo image has it)

DB_NAME=${MONGODB_DATABASE:-marketplace}
CONTAINER=${MONGO_CONTAINER:-mongo-db}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="dumps/mongodb/${TIMESTAMP}"

mkdir -p "${OUT_DIR}"

echo "[+] Dumping MongoDB database '${DB_NAME}' from container '${CONTAINER}'"

# Run mongodump inside container and copy archive out
docker compose exec -T "${CONTAINER}" mongodump --db "${DB_NAME}" --archive > "${OUT_DIR}/dump.archive"

echo "[+] Dump complete: ${OUT_DIR}/dump.archive"

echo "Restore example:"
echo "  docker compose exec -T ${CONTAINER} mongorestore --archive < ${OUT_DIR}/dump.archive"
