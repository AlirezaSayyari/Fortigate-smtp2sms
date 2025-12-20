#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

docker compose build --pull --no-cache
docker compose up -d --force-recreate --remove-orphans
docker image prune -f
docker builder prune -f
