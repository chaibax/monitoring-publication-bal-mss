#!/usr/bin/env bash
# Remontée humaine d'une panne de l'outil, par ticket GitHub.
#
#   alerte.sh ouvrir <étiquette> <titre> <corps>
#   alerte.sh fermer <étiquette> <commentaire>
#
# Pourquoi un ticket. Deux pannes de l'outil (10-16 octobre, 17-25 novembre
# 2026) ont été détectées par la vigie dès le premier jour, puis sont restées
# sans suite une semaine : l'échec d'une tâche planifiée ne produit qu'un
# courriel générique de GitHub, noyé, et le webhook Slack n'a jamais été posé.
# Un ticket qui mentionne le propriétaire du dépôt produit une notification
# nominative, reste ouvert et visible tant que la panne dure, et se ferme seul
# au rétablissement. Voir docs/journal.md, décision 12.
#
# Idempotent : un seul ticket ouvert par étiquette, quel que soit le nombre
# d'échecs ; pas de commentaire à chaque exécution, pour ne pas habituer à
# ignorer les notifications.
#
# Requiert GH_TOKEN (le jeton du workflow suffit, avec `issues: write`) et
# GITHUB_REPOSITORY.

set -euo pipefail

action=$1
etiquette=$2
depot=${GITHUB_REPOSITORY:?}

gh label create "$etiquette" --repo "$depot" --color B60205 \
  --description "Panne de l'outil de supervision (ticket automatique)" --force >/dev/null

ouvert=$(gh issue list --repo "$depot" --label "$etiquette" --state open \
  --json number --jq '.[0].number // empty')

case "$action" in
  ouvrir)
    titre=$3
    corps=$4
    if [ -n "$ouvert" ]; then
      echo "Ticket #$ouvert déjà ouvert pour « $etiquette » — rien de plus."
      exit 0
    fi
    gh issue create --repo "$depot" --label "$etiquette" --title "$titre" --body "$corps"
    ;;
  fermer)
    commentaire=$3
    if [ -z "$ouvert" ]; then
      echo "Aucun ticket ouvert pour « $etiquette »."
      exit 0
    fi
    gh issue close "$ouvert" --repo "$depot" --comment "$commentaire"
    ;;
  *)
    echo "usage : alerte.sh ouvrir|fermer <étiquette> …" >&2
    exit 2
    ;;
esac
