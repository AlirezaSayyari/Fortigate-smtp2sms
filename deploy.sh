#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

docker compose --env-file .env_production build --pull --no-cache
docker compose --env-file .env_production up -d --force-recreate --remove-orphans
docker image prune -f
docker builder prune -f
