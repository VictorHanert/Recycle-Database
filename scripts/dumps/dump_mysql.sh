#!/usr/bin/env bash
set -euo pipefail

# Dump MySQL database running in docker-compose service mysql-database
# Usage command: ./scripts/dumps/dump_mysql.sh
# Output: dumps/mysql/<timestamp>/marketplace.sql
# Includes schema, stored procedures, triggers, views, events, and data

DB_NAME=${MYSQL_DATABASE:-marketplace}
CONTAINER=${MYSQL_CONTAINER:-mysql-db}
USER=${MYSQL_USER:-root}
PASS=${MYSQL_PASS:-root}
HOST=${MYSQL_HOST:-mysql-db}
PORT=${MYSQL_PORT:-3306}
NETWORK=${MYSQL_NETWORK:-fullstack_project_default}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="dumps/mysql/${TIMESTAMP}"

mkdir -p "${OUT_DIR}"

echo "[+] Dumping MySQL database '${DB_NAME}' from container '${CONTAINER}' as user '${USER}'"

if docker compose ps -q "${CONTAINER}" >/dev/null 2>&1 && [ -n "$(docker compose ps -q "${CONTAINER}")" ]; then
  # Exec into local compose container
  docker compose exec -T "${CONTAINER}" mysqldump \
    -u "${USER}" -p"${PASS}" \
    --routines \
    --triggers \
    --events \
    --single-transaction \
    --databases "${DB_NAME}" > "${OUT_DIR}/marketplace.sql"
else
  echo "[i] Container '${CONTAINER}' not in this compose. Using network '${NETWORK}' to host '${HOST}:${PORT}'."
  # Optional network check
  if ! docker network inspect "${NETWORK}" >/dev/null 2>&1; then
    echo "[!] Docker network '${NETWORK}' not found. Set MYSQL_NETWORK to the correct network and retry." && exit 1
  fi
  docker run --rm --network "${NETWORK}" mysql:8 mysqldump \
    -h "${HOST}" -P "${PORT}" \
    -u"${USER}" -p"${PASS}" \
    --routines \
    --triggers \
    --events \
    --single-transaction \
    "${DB_NAME}" > "${OUT_DIR}/marketplace.sql"
fi

echo "[+] Dump complete: ${OUT_DIR}/marketplace.sql"

echo "Restore example:"
echo "  docker compose exec -T ${CONTAINER} mysql -u root -proot < ${OUT_DIR}/marketplace.sql"
