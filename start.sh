#!/bin/bash
# v2 'claws' marketplace. Seed the DATASET variant (default: old), then serve.
# DB lives on ephemeral disk, so seed every boot. Restarting the service
# reseeds from scratch — that is also how state (bans) is reset between
# conditions. Switch dataset: set DATASET=new in Render env vars + redeploy.
DS=${DATASET:-old}
if [ "$DS" = "new" ]; then SEED=20261029; else SEED=20261025; fi
python seed.py --variant "$DS" --seed "$SEED" --db /tmp/market.sqlite3 --labels /tmp/labels.json
export MARKETPLACE_DB=/tmp/market.sqlite3
export DISABLE_AUTH=1
exec python app.py
