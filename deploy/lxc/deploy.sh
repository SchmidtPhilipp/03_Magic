#!/usr/bin/env bash
# Idempotente Deploy-Hilfe für den LXC-Container (Debian 12 getestet).
# Führt das Setup aus, legt Env/Service an und startet den Dienst.
# Ausführen als root innerhalb des Containers, idealerweise im Repo-Root.

set -euo pipefail

APP_USER="${APP_USER:-mtgapp}"
APP_HOME="${APP_HOME:-/opt/mtg-optimizer}"
REPO_SOURCE="${REPO_SOURCE:-$(pwd)}"
VENV_PATH="${VENV_PATH:-${APP_HOME}/venv}"
ENV_FILE="${ENV_FILE:-/etc/mtg-optimizer.env}"
SERVICE_PATH="${SERVICE_PATH:-/etc/systemd/system/mtg-optimizer.service}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Dieses Skript muss als root laufen." >&2
  exit 1
fi

echo "==> Starte Setup (User=${APP_USER}, Ziel=${APP_HOME})"
APP_USER="${APP_USER}" APP_HOME="${APP_HOME}" REPO_SOURCE="${REPO_SOURCE}" VENV_PATH="${VENV_PATH}" \
  bash deploy/lxc/setup.sh

if [ ! -f "${ENV_FILE}" ]; then
  echo "==> Lege Env-Datei an (${ENV_FILE})"
  cp deploy/lxc/mtg-optimizer.env.example "${ENV_FILE}"
  echo "   Bitte SECRET_KEY/PORT etc. in ${ENV_FILE} anpassen."
fi

if [ ! -f "${SERVICE_PATH}" ]; then
  echo "==> Installiere systemd-Service (${SERVICE_PATH})"
  cp deploy/lxc/mtg-optimizer.service "${SERVICE_PATH}"
fi

echo "==> systemd neu laden"
systemctl daemon-reload

echo "==> Service aktivieren und starten"
systemctl enable --now mtg-optimizer.service

echo "==> Status"
systemctl status mtg-optimizer.service --no-pager -l || true

echo "==> Fertig. Aufruf: http://<LXC-IP>:${PORT:-5050}"

