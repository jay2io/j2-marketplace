#!/bin/bash
# Seed the invasion selected by $INVASION (default: heldout), then serve.
# DB lives on ephemeral disk, so seed every boot. Restarting the service
# reseeds from scratch — that is also how state (bans) is reset between
# held-out conditions.
INV=${INVASION:-heldout}
if [ "$INV" = "train" ]; then SEED=42; else SEED=1337; fi
python seed.py --invasion "$INV" --seed "$SEED" --db /tmp/market.sqlite3 --labels /tmp/labels.json
export MARKETPLACE_DB=/tmp/market.sqlite3
export DISABLE_AUTH=1
exec python app.py
