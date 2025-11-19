#!/usr/bin/env bash
set -euo pipefail

# Dump MySQL database running in docker-compose service mysql-database
# Usage command: ./scripts/dumps/dump_mysql.sh
# Output: dumps/mysql/<timestamp>/marketplace.sql
# Includes schema, stored procedures, triggers, views, events, and data

DB_NAME=${MYSQL_DATABASE:-marketplace}
CONTAINER=${MYSQL_CONTAINER:-mysql-database}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="dumps/mysql/${TIMESTAMP}"

mkdir -p "${OUT_DIR}"

echo "[+] Dumping MySQL database '${DB_NAME}' from container '${CONTAINER}'"

# Dump with routines, triggers, events, and data
docker compose exec -T "${CONTAINER}" mysqldump \
  -u root -proot \
  --routines \
  --triggers \
  --events \
  --single-transaction \
  --databases "${DB_NAME}" > "${OUT_DIR}/marketplace.sql"

echo "[+] Dump complete: ${OUT_DIR}/marketplace.sql"

echo "Restore example:"
echo "  docker compose exec -T ${CONTAINER} mysql -u root -proot < ${OUT_DIR}/marketplace.sql"
