#!/usr/bin/env bash
set -euo pipefail

# Basic, repeatable setup for running inside a Proxmox LXC (Debian 12 tested).
# Run as root inside the container.

APP_USER="${APP_USER:-mtgapp}"
APP_HOME="${APP_HOME:-/opt/mtg-optimizer}"
REPO_SOURCE="${REPO_SOURCE:-$(pwd)}"
VENV_PATH="${VENV_PATH:-${APP_HOME}/venv}"

echo "==> Installing system packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip \
  build-essential libxml2-dev libxslt-dev zlib1g-dev \
  libjpeg-dev libfreetype6-dev pkg-config \
  rsync git curl

echo "==> Creating application user/group (${APP_USER})"
if ! id "${APP_USER}" >/dev/null 2>&1; then
  adduser --system --group --home "${APP_HOME}" "${APP_USER}"
fi

echo "==> Creating directories"
install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_HOME}" /var/log/mtg-optimizer

# Copy repository into /opt/mtg-optimizer unless we are already there
if [ "$(realpath "${REPO_SOURCE}")" != "$(realpath "${APP_HOME}")" ]; then
  echo "==> Syncing repository to ${APP_HOME}"
  rsync -a --delete \
    --exclude 'venv' \
    --exclude '__pycache__' \
    "${REPO_SOURCE}/" "${APP_HOME}/"
fi

cd "${APP_HOME}"

echo "==> Creating virtual environment"
python3 -m venv "${VENV_PATH}"
"${VENV_PATH}/bin/pip" install --upgrade pip

echo "==> Installing Python dependencies"
"${VENV_PATH}/bin/pip" install --no-cache-dir -r requirements.txt

echo "==> Adjusting ownership"
chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" /var/log/mtg-optimizer

echo "==> Done. Configure /etc/mtg-optimizer.env and install the systemd unit:"
echo "    cp deploy/lxc/mtg-optimizer.service /etc/systemd/system/"
echo "    cp deploy/lxc/mtg-optimizer.env.example /etc/mtg-optimizer.env"
echo "    systemctl daemon-reload && systemctl enable --now mtg-optimizer"

