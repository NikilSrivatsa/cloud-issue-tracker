#!/usr/bin/env bash
set -euo pipefail

APP_IMAGE="${APP_IMAGE:-cloud-issue-tracker:latest}"
APP_CONTAINER="${APP_CONTAINER:-cloud-issue-tracker}"

sudo mkdir -p /opt/cloud-issue-tracker/data

if sudo docker ps -a --format '{{.Names}}' | grep -q "^${APP_CONTAINER}$"; then
  sudo docker stop "${APP_CONTAINER}" || true
  sudo docker rm "${APP_CONTAINER}" || true
fi

sudo docker load -i /tmp/cloud-issue-tracker.tar
sudo docker run -d \
  --name "${APP_CONTAINER}" \
  --restart unless-stopped \
  -p 80:5000 \
  -v /opt/cloud-issue-tracker/data:/data \
  -e SECRET_KEY="${SECRET_KEY:-production-secret-change-me}" \
  "${APP_IMAGE}"
