#!/usr/bin/env bash

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <hostname>" >&2
  exit 1
fi

if [ -z "${CERT_APPROLE_ID:-}" ]; then
    echo CERT_APPROLE_ID is not defined
    exit 1
fi

HOST="$1"
APP_PREFIX='/opt/apps/ustreamer'

echo "Deploying to $HOST..."

echo "Creating directories..."
ssh $HOST mkdir -p -m 755 "${APP_PREFIX}"

echo "Syncing ${APP_PREFIX}..."
rsync -Dlprt --progress \
    compose.yaml \
    nginx.conf \
    "${HOST}:${APP_PREFIX}/"

echo "Bringing up compose..."
ssh $HOST 'docker network create vaultnet 2>/dev/null || true'
ssh $HOST "(cd '${APP_PREFIX}' && docker compose pull && docker compose up -d --force-recreate)"

echo "Done"
