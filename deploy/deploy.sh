#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/www/thinkland}"
BRANCH="${DEPLOY_BRANCH:-main}"
BACKEND_SERVICE="${BACKEND_SERVICE:-thinkland-backend}"

echo "==> Deploy ThinkLand"
echo "APP_DIR=${APP_DIR}"
echo "BRANCH=${BRANCH}"

cd "${APP_DIR}"

echo "==> Pull latest code"
git fetch origin "${BRANCH}"
git reset --hard "origin/${BRANCH}"

echo "==> Prepare backend"
cd "${APP_DIR}/consumer-backend"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if command -v mysql >/dev/null 2>&1; then
  echo "==> Run database SQL"
  mysql < sql/init.sql
  for migration in sql/[0-9]*.sql; do
    if [ -f "${migration}" ]; then
      mysql < "${migration}"
    fi
  done
else
  echo "mysql command not found, skip database SQL"
fi

echo "==> Build frontend"
cd "${APP_DIR}/consumer-front"
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi
npm run build

echo "==> Restart backend"
sudo systemctl restart "${BACKEND_SERVICE}"

echo "==> Reload nginx"
sudo nginx -t
sudo systemctl reload nginx

echo "==> Deploy done"
