#!/usr/bin/env bash
set -e
RESULT_DIR="results"
BW=10         # Mbps
DELAY=50ms    # ms
TIME=20       # s

mkdir -p "$RESULT_DIR"

declare -a RENOS=(1 2 2)
declare -a BBRS=(1 2 1)

for i in 0 1 2; do
    DIR="$RESULT_DIR/comp$((i+1))"
    mkdir -p "$DIR"
    sudo mn -c >/dev/null 2>&1      # limpa estado anterior
    echo ">>> cenário $((i+1)) → $DIR"
    sudo python3 competition.py \
        --bw "$BW" --delay "$DELAY" --time "$TIME" \
        --reno "${RENOS[$i]}" --bbr "${BBRS[$i]}" \
        --output "$DIR"
done
