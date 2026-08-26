#!/usr/bin/env bash
# Prépare le dossier publié : DSFR auto-hébergé + agrégats.
set -euo pipefail
cd "$(dirname "$0")"
bash fetch-dsfr.sh
rm -rf data && mkdir -p data/daily
cp ../data/calendrier-publications.json data/
cp ../data/daily/*.json data/daily/ 2>/dev/null || true
INSTANTANE=$(ls -1 ../data/snapshots/*.json 2>/dev/null | tail -1)
[ -n "$INSTANTANE" ] && cp "$INSTANTANE" data/instantane.json
# Index des jours disponibles : la page est statique, elle ne peut pas lister un dossier.
python3 - <<'PY'
import json, os
jours = sorted(f[:-5] for f in os.listdir("data/daily") if f.endswith(".json"))
instantane = "instantane.json" if os.path.exists("data/instantane.json") else None
json.dump({"jours": jours, "instantane": instantane},
          open("data/index.json", "w"), ensure_ascii=False)
print(f"{len(jours)} jour(s) d'agrégats publiés")
PY
