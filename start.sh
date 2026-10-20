#!/bin/bash
# Seed the train invasion, then serve. DB lives on ephemeral disk, so seed every boot.
python seed.py --invasion train --seed 42 --db /tmp/market.sqlite3 --labels /tmp/labels.json
export MARKETPLACE_DB=/tmp/market.sqlite3
export DISABLE_AUTH=1
exec python app.py
