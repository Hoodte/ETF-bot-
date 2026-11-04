#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu 22.04/24.04 VPS: installs Python, the ETF bot, and n8n as a service.
# Run as root:  bash setup_vps.sh
# n8n listens on localhost only. Reach it from your laptop with an SSH tunnel (see deploy/README.md).
set -euo pipefail

REPO="https://github.com/Hoodte/etf-bot-.git"   # if you make the repo private, use a deploy key instead
BOT_DIR=/opt/etf-bot
SVC_USER=n8n

apt-get update
apt-get install -y git python3 python3-venv python3-pip curl ca-certificates

# Node.js 22 LTS for n8n
if ! command -v node >/dev/null || [ "$(node -v | cut -c2- | cut -d. -f1)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
npm install -g n8n

id -u "$SVC_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$SVC_USER"

# The bot
if [ ! -d "$BOT_DIR/.git" ]; then git clone "$REPO" "$BOT_DIR"; fi
python3 -m venv "$BOT_DIR/.venv"
"$BOT_DIR/.venv/bin/pip" install --upgrade pip
"$BOT_DIR/.venv/bin/pip" install -r "$BOT_DIR/requirements.txt" -r "$BOT_DIR/requirements-extras.txt"
chown -R "$SVC_USER:$SVC_USER" "$BOT_DIR"

# n8n service. Execute Command and $env access are needed by the workflow; newer n8n versions
# may disable them by default, so they are enabled explicitly here.
cat >/etc/systemd/system/n8n.service <<EOF
[Unit]
Description=n8n
After=network-online.target

[Service]
User=$SVC_USER
Environment=N8N_LISTEN_ADDRESS=127.0.0.1
Environment=N8N_PORT=5678
Environment=GENERIC_TIMEZONE=Europe/London
Environment=TZ=Europe/London
Environment=NODES_EXCLUDE=[]
Environment=N8N_BLOCK_ENV_ACCESS_IN_NODE=false
EnvironmentFile=-/etc/n8n.env
ExecStart=$(command -v n8n) start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Secrets live here, readable by root and n8n only. Fill in TELEGRAM_CHAT_ID (and later T212 keys).
if [ ! -f /etc/n8n.env ]; then
  printf 'TELEGRAM_CHAT_ID=\n# T212_API_KEY=\n# T212_API_SECRET=\n' >/etc/n8n.env
  chown root:"$SVC_USER" /etc/n8n.env
  chmod 640 /etc/n8n.env
fi

systemctl daemon-reload
systemctl enable --now n8n

echo
echo "Done. Next:"
echo "  1. Test the bot:   sudo -u $SVC_USER bash -c 'cd $BOT_DIR && .venv/bin/python -m etfbot check-data'"
echo "  2. Edit /etc/n8n.env, then: systemctl restart n8n"
echo "  3. From your laptop: ssh -L 5678:127.0.0.1:5678 root@<vps-ip>  then open http://localhost:5678"
