#!/usr/bin/env bash
# Construit le site et le met en production, en deux temps.
#
# `netlify deploy --prod` n'est plus utilisable. Depuis le 2026-09-04, le
# chemin « --prod » du CLI se fait refuser par l'API — un « JSONHTTPError:
# Forbidden » émis avant même que la construction ne démarre, sans corps de
# réponse exploitable. Mesuré le 2026-09-07 : le jeton lit tout (sept points
# d'API en 200), construit, téléverse, et publie un déploiement existant sans
# difficulté. Seul le chemin « --prod » du CLI échoue.
#
# La publication est donc décomposée en deux opérations dont on a la preuve
# qu'elles passent : le CLI construit et téléverse, l'API bascule ensuite le
# déploiement en production. Voir la décision 8 du journal.
#
# Effet de bord à connaître : créé sans « --prod », le déploiement porte le
# contexte « deploy-preview » alors même qu'il est celui que sert le domaine
# de production. C'est sans conséquence tant que `netlify.toml` ne définit
# aucun bloc `[context.production]` — il n'en a aucun. Le jour où il en aura
# un, il faudra le savoir : il ne s'appliquerait pas.
set -euo pipefail

: "${NETLIFY_AUTH_TOKEN:?jeton de déploiement absent}"
: "${NETLIFY_SITE_ID:?identifiant de projet absent}"

# Version figée : le comportement du CLI ne doit pas dériver sous nos pieds au
# gré des publications amont, sur une étape qui ne s'exécute qu'une fois par
# jour et sans personne pour la regarder.
CLI="netlify-cli@26.2.0"
API="https://api.netlify.com/api/v1"

# Les journaux d'exécution d'un dépôt public sont lisibles par tous : rien
# n'en sort qui ne soit déjà public, et les identifiants longs sont masqués.
masquer() { sed -E 's/[A-Za-z0-9_-]{40,}/[MASQUE]/g'; }

# Diagnostic volontairement muet sur les noms de projet. Un jeton qui
# n'appartient pas au bon compte Netlify se signale ici, avant toute
# tentative, plutôt que par un refus opaque trois étapes plus loin.
npx --yes "$CLI" api listSites --data '{}' \
  | python3 -c "import json,sys,os; s=json.load(sys.stdin); cible=os.environ['NETLIFY_SITE_ID']; visible=any(p['id']==cible for p in s); print(f'Jeton : {len(s)} projet(s) accessible(s), projet cible {\"visible\" if visible else \"INVISIBLE — le jeton appartient probablement à un autre compte Netlify\"}.')"

# Premier temps : construire et téléverser. Sans « --prod », le déploiement
# est créé mais reste en brouillon, sur une URL éphémère.
sortie=$(npx --yes "$CLI" deploy --site "$NETLIFY_SITE_ID" --json)

# Le CLI peut précéder son JSON de lignes de construction : on retient le
# premier objet complet qui porte un identifiant de déploiement, plutôt que de
# parier sur la sortie entière.
deploiement=$(printf '%s' "$sortie" | python3 -c '
import json, sys
brut = sys.stdin.read()
decodeur = json.JSONDecoder()
for i, c in enumerate(brut):
    if c != "{":
        continue
    try:
        objet, _ = decodeur.raw_decode(brut[i:])
    except ValueError:
        continue
    if isinstance(objet, dict) and "deploy_id" in objet:
        print(objet["deploy_id"])
        break
else:
    sys.exit("identifiant de déploiement introuvable dans la sortie du CLI")
')

# Second temps : basculer ce déploiement en production.
corps=$(mktemp)
code=$(curl -sS -X POST -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -o "$corps" -w '%{http_code}' \
  "$API/sites/$NETLIFY_SITE_ID/deploys/$deploiement/restore")

if [ "$code" != "200" ]; then
  # Le corps de la réponse est la seule chose qui dise pourquoi. Le faire
  # sortir, c'est s'épargner la journée d'enquête qu'a coûtée le refus muet
  # du CLI.
  echo "::error::Mise en production refusée (HTTP $code) : $(head -c 600 "$corps" | tr -d '\n' | masquer)"
  exit 1
fi

echo "Site publié — déploiement $deploiement."
