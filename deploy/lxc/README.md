LXC Deployment (Proxmox)
========================

Ziel
----
Bereitstellung der MTG Sealed Deck Optimizer Web-App in einem Proxmox-LXC-Container (getestet mit Debian 12 Template). Die Anleitung nutzt systemd + venv, kein Docker erforderlich.

Quick Steps (TL;DR)
-------------------
1) Proxmox: LXC anlegen (Debian 12, unprivileged ok, nesting=1 empfohlen). Mind. 2 vCPU, 2-4 GB RAM, 8+ GB Storage. Bridge (z. B. vmbr0) und Option „Nesting“ aktivieren.  
2) Container starten, ins LXC einloggen.  
3) Repository in den Container kopieren oder direkt git-clonen nach `/opt/mtg-optimizer`.  
4) Als root im Repo ausführen:
   ```
   cd /opt/mtg-optimizer
   bash deploy/lxc/setup.sh
   cp deploy/lxc/mtg-optimizer.env.example /etc/mtg-optimizer.env
   nano /etc/mtg-optimizer.env   # Port/Secret anpassen
   cp deploy/lxc/mtg-optimizer.service /etc/systemd/system/
   systemctl daemon-reload
   systemctl enable --now mtg-optimizer.service
   ```
5) Im Browser `http://<LXC-IP>:5050` aufrufen (Port ggf. im Env ändern).

Proxmox-Host One-Liner (ähnlich community-scripts)
--------------------------------------------------
Auf dem Proxmox-Host als root (community-scripts Stil):
```
CTID=1999 HOSTNAME=mtg-optimizer REPO_URL="https://github.com/<owner>/<repo>.git" \
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/deploy/lxc/proxmox-create.sh)"
```
- `REPO_URL` ist Pflicht (Git-URL deines Projekts). `REPO_BRANCH` optional (`main`).  
- Weitere optionale Variablen: `STORAGE` (local-lvm), `DISK_GB` (12), `CORES` (2), `MEMORY_MB` (4096), `SWAP_MB` (512), `BRIDGE` (vmbr0), `NET_IP` (dhcp), `NET_GW` (leer), `FEATURES` (nesting=1).  
- CT wird mit Debian-12-Template, Nesting=1, DHCP auf vmbr0 erstellt, klont das Repo nach `/opt/mtg-optimizer` und startet innen `deploy/lxc/deploy.sh`.

Was das Setup-Script macht
--------------------------
- Installiert System-Pakete (Python, Build-Deps, rsync, git, curl)  
- Legt User/Group `mtgapp` an und erstellt `/opt/mtg-optimizer` + `/var/log/mtg-optimizer`  
- Optionales Sync aus dem aktuellen Repo-Verzeichnis nach `/opt/mtg-optimizer`  
- Erstellt venv unter `/opt/mtg-optimizer/venv` und installiert `requirements.txt`  
- Setzt Ownership auf `mtgapp:mtgapp`

Systemd Service
---------------
- Service-Datei: `deploy/lxc/mtg-optimizer.service`  
- Läuft als User `mtgapp`, WorkingDir `/opt/mtg-optimizer`, nutzt venv  
- Liest Variablen aus `/etc/mtg-optimizer.env` (siehe Example)  
- Log-Ausgabe landet in `/var/log/mtg-optimizer/app.log` und `app.err.log`

Ports & Netzwerk
----------------
- Default-Port: 5050 (`PORT` in `/etc/mtg-optimizer.env` änderbar)  
- Host in `config.py` ist jetzt per Env (`HOST`, default `0.0.0.0`) steuerbar  
- Hinter Reverse Proxy (nginx/traefik) einfach per TCP-Forwarding oder HTTP-Proxy terminieren

Updates / Redeploy
------------------
```
cd /opt/mtg-optimizer
git pull                # falls Repo per Git liegt
bash deploy/lxc/setup.sh
systemctl restart mtg-optimizer.service
```

Backups / Persistenz
--------------------
- Wichtige Pfade: `uploads/`, `logs/`, `data/` und ggf. `static/card_cache/`.  
- Bei LXC kann ein zusätzlicher Mountpoint (z. B. `/mnt/mtg-data`) definiert und in `/opt/mtg-optimizer` gemountet werden, falls gewünscht.

Troubleshooting
---------------
- Service-Status: `systemctl status mtg-optimizer.service`  
- Logs: `journalctl -u mtg-optimizer.service -f` oder Dateien unter `/var/log/mtg-optimizer/`  
- Port prüfen: `ss -tlnp | grep 5050`

Notes zu Proxmox-LXC
--------------------
- Für `requests`/`lxml`/`pandas` etc. reicht Debian 12 + Build-Essentials.  
- Wenn unprivileged Container: sicherstellen, dass `fuse`/`cgroups` laut Proxmox-Doku passen; für diesen Dienst werden keine speziellen Kernel-Features benötigt.  
- Bei sehr großen Card-Collections Speicher entsprechend erhöhen (Pandas). 

