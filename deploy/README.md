# Running the ETF bot daily on a VPS with n8n

The bot is plain Python. n8n runs it every weekday after the London close and sends you a Telegram summary. Paper mode only until a strategy passes the backtest and paper-trade gates.

## What you need

- A small Linux VPS running Ubuntu 22.04 or 24.04. 1 vCPU and 1–2 GB RAM is enough.
- A Telegram bot for alerts: message `@BotFather`, send `/newbot`, and keep the token. Message your new bot once, then get your chat ID (for example from `@userinfobot`).

## 1. Set up the VPS (about 10 minutes)

```
ssh root@<vps-ip>
curl -fsSLO https://raw.githubusercontent.com/Hoodte/etf-bot-/main/deploy/setup_vps.sh
bash setup_vps.sh
```

This installs Python, the bot (in `/opt/etf-bot`) and n8n as a service. n8n only listens on the VPS itself, so it isn't exposed to the internet.

Then check the data works:

```
sudo -u n8n bash -c 'cd /opt/etf-bot && .venv/bin/python -m etfbot check-data'
```

`"ok": true` means you're ready. If not, see "Data source" in the main README.

## 2. Add your Telegram chat ID

```
nano /etc/n8n.env          # set TELEGRAM_CHAT_ID=123456789
systemctl restart n8n
```

## 3. Open n8n from your laptop

```
ssh -L 5678:127.0.0.1:5678 root@<vps-ip>
```

Leave that window open, browse to http://localhost:5678, and create your n8n owner account.

## 4. Import the workflows

1. **Credentials → New → Telegram API**: paste the BotFather token and name it `Telegram account`.
2. **Workflows → Import from file**: import `deploy/n8n_error_workflow.json`, then `deploy/n8n_etfbot_workflow.json`.
3. In each Telegram node, pick the `Telegram account` credential.
4. Open the daily workflow, go to **Settings → Error workflow**, and choose `ETF bot: error alerts`.
5. Click **Execute workflow** once to test, then switch the workflow to **Active**.

## What the daily workflow does

| Step | Node | If it fails |
| --- | --- | --- |
| 1 | Weekdays 17:15 UK time | — |
| 2 | `market-status`: is the London market open? | Closed: stops quietly |
| 3 | `check-data`: data quality | Telegram alert listing the issues, no trading |
| 4 | `paper`: signal → risk check → paper fills | Failure message |
| 5 | Telegram summary: equity, cash, fills, risk rejections | — |
| any | Error workflow | Telegram alert with the failing node |

Paper positions are saved in `/opt/etf-bot/state/` on the VPS, and logs in `/opt/etf-bot/logs/`.

## Updating the bot

```
sudo -u n8n bash -c 'cd /opt/etf-bot && git pull && .venv/bin/pip install -r requirements.txt -r requirements-extras.txt'
```

Updates are manual on purpose, so a code change never reaches the daily run without you choosing it.

## Notes

- **Emergency stop:** `touch /opt/etf-bot/state/KILL`. Nothing trades while that file exists.
- **Switching to the Trading 212 demo later:** add `T212_API_KEY` and `T212_API_SECRET` to `/etc/n8n.env`, fill in the `t212_ticker` values in `config.yaml`, and change the "Run paper trade" node's command from `paper` to `trade`.
- If the **Execute Command** node is missing in n8n, check that `NODES_EXCLUDE=[]` is set in `/etc/systemd/system/n8n.service`. The setup script sets it, because newer n8n versions may disable that node by default.
- The repo is currently **public**. Make it private before any broker keys or account details go near it, and switch the clone to a deploy key.
