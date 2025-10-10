#!/bin/bash
cd /workspaces/oews/data
for f in *.xlsx.backup; do
    base=${f%.backup}
    cp "$f" "$base"
    echo "Restored $base"
done
