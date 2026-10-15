#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

read_env() {
    grep -m1 "^$1=" .env | cut -d= -f2-
}

TELEGRAM_BOT_TOKEN="$(read_env TELEGRAM_BOT_TOKEN)"
ADMIN_CHAT_ID="$(read_env ADMIN_CHAT_ID)"
BACKUP_PAR_URL="$(read_env BACKUP_PAR_URL)"

TIMESTAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
FILE_NAME="filingbot-${TIMESTAMP}.dump"
DUMP_FILE="$(mktemp)"

notify_admin() {
    curl --silent --max-time 20 \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${ADMIN_CHAT_ID}" \
        --data-urlencode "text=$1" > /dev/null || true
}

on_failure() {
    echo "$(date -u) backup FAILED at line $1" >&2
    notify_admin "FilingBot backup FAILED at line $1 on $(hostname) (${TIMESTAMP})"
}

trap 'on_failure $LINENO' ERR
trap 'rm -f "$DUMP_FILE"' EXIT

echo "$(date -u) starting backup ${FILE_NAME}"

docker compose exec -T postgres \
    sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DUMP_FILE"

if [ ! -s "$DUMP_FILE" ]; then
    echo "dump file is empty" >&2
    false
fi

docker compose exec -T postgres pg_restore --list < "$DUMP_FILE" > /dev/null

curl --fail --silent --show-error --max-time 300 --retry 3 \
    --upload-file "$DUMP_FILE" "${BACKUP_PAR_URL}${FILE_NAME}"

echo "$(date -u) backup uploaded: ${FILE_NAME} ($(du -h "$DUMP_FILE" | cut -f1))"
