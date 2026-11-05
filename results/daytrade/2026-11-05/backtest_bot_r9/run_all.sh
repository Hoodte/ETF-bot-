#!/bin/bash
cd /home/claude/backtest-bot
export NO_PROXY="localhost,127.0.0.1" no_proxy="localhost,127.0.0.1" PYTHONPATH=.
declare -A SPR=( [EURUSD]=0.00008 [GBPUSD]=0.0001 [USDJPY]=0.01 [AUDUSD]=0.00009 [USDCAD]=0.0001 [XAUUSD]=0.25 [NAS100]=1.5 [SPX500]=0.5 [DAX]=1.5 )
for job in "$@"; do
  pair=${job%:*}; tf=${job#*:}
  python3 scripts/run_discovery_qqq.py --pair $pair --timeframe $tf --source histdata --start 2016-01-01 --end 2024-12-31 \
     --spread ${SPR[$pair]} --run-id ${pair,,}_${tf,,}_histdata_r9 > /tmp/bb/${pair}_${tf}.log 2>&1
  echo "$pair $tf done $(date +%H:%M)" >> /tmp/bb/progress.log
done
