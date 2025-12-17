#!/usr/bin/env bash
# Proxmox host helper to create an LXC (Debian 12) and deploy MTG Optimizer inside.
# Inspired by community-scripts style. Run directly on the Proxmox host as root.
#
# Usage (community-scripts style one-liner):
#   CTID=1999 HOSTNAME=mtg-optimizer REPO_URL="https://github.com/<owner>/<repo>.git" \
#     bash -c "$(curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/deploy/lxc/proxmox-create.sh)"
#
# Optional env vars:
#   CTID (1999), HOSTNAME (mtg-optimizer), STORAGE (local-lvm), DISK_GB (12),
#   CORES (2), MEMORY_MB (4096), SWAP_MB (512), BRIDGE (vmbr0), NET_IP (dhcp),
#   NET_GW (none), REPO_BRANCH (main), TEMPLATE_STORAGE (local), FEATURES (nesting=1)

set -euo pipefail

CTID="${CTID:-1999}"
HOSTNAME="${HOSTNAME:-mtg-optimizer}"
STORAGE="${STORAGE:-local-lvm}"
DISK_GB="${DISK_GB:-12}"
CORES="${CORES:-2}"
MEMORY_MB="${MEMORY_MB:-4096}"
SWAP_MB="${SWAP_MB:-512}"
BRIDGE="${BRIDGE:-vmbr0}"
NET_IP="${NET_IP:-dhcp}"
NET_GW="${NET_GW:-}"
REPO_URL="${REPO_URL:-}"
REPO_BRANCH="${REPO_BRANCH:-main}"
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
FEATURES="${FEATURES:-nesting=1}"

fail() { echo "ERROR: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "Dieses Skript muss auf dem Proxmox-Host als root laufen."
command -v pct >/dev/null || fail "pct nicht gefunden (Proxmox Umgebung erforderlich)."
command -v pveam >/dev/null || fail "pveam nicht gefunden."
[ -n "${REPO_URL}" ] || fail "REPO_URL muss gesetzt werden (Git-URL des Projekts)."

echo "==> Prüfe verfügbares Debian-12 Template"
TEMPLATE="$(pveam available | awk '/debian-12-standard/ {print $2; exit}')"
[ -n "${TEMPLATE}" ] || fail "Kein debian-12-standard Template gefunden (pveam available)."

if ! pveam list "${TEMPLATE_STORAGE}" | grep -q "${TEMPLATE}"; then
  echo "==> Lade Template: ${TEMPLATE}"
  pveam download "${TEMPLATE_STORAGE}" "${TEMPLATE}"
fi

[ -z "$(pct list | awk -v id="${CTID}" '$1==id')" ] || fail "CT ID ${CTID} existiert bereits."

NET_CFG="name=eth0,bridge=${BRIDGE},ip=${NET_IP}"
[ -n "${NET_GW}" ] && NET_CFG="${NET_CFG},gw=${NET_GW}"

echo "==> Erstelle Container CT${CTID} (${HOSTNAME})"
pct create "${CTID}" "${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE}" \
  -hostname "${HOSTNAME}" \
  -features "${FEATURES}" \
  -unprivileged 1 \
  -cores "${CORES}" \
  -memory "${MEMORY_MB}" \
  -swap "${SWAP_MB}" \
  -rootfs "${STORAGE}:${DISK_GB}" \
  -net0 "${NET_CFG}" \
  -password "" \
  -onboot 1

echo "==> Starte CT${CTID}"
pct start "${CTID}"

echo "==> Warte auf Netzwerk"
sleep 5

echo "==> Installiere Basis-Pakete im CT"
pct exec "${CTID}" -- bash -c "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y git curl"

echo "==> Klone/Pull Repo"
pct exec "${CTID}" -- bash -c "cd /opt && if [ -d mtg-optimizer/.git ]; then cd mtg-optimizer && git pull; else git clone --branch '${REPO_BRANCH}' '${REPO_URL}' mtg-optimizer; fi"

echo "==> Starte Deployment im CT"
pct exec "${CTID}" -- bash -c "cd /opt/mtg-optimizer && bash deploy/lxc/deploy.sh"

echo "==> Fertig. CT${CTID} sollte auf Port 5050 (oder .env) lauschen."
echo "     IP ermitteln: pct exec ${CTID} -- hostname -I"

