"""Contrôle avant commit — §11 du brief.

Le dépôt est public et alimenté par un robot. Une donnée à caractère
personnel commitée par erreur reste dans l'historique Git même après
suppression, et devient indexable. Une revue humaine ne suffit pas.

Ce contrôle refuse tout fichier de `data/` qui dépasse une taille plafond
ou qui contient un motif ressemblant à une adresse de messagerie. Il est
volontairement grossier : mieux vaut bloquer un cycle que publier un nom.

    python -m ingest.garde_fou data/daily/2026-08-26.json …
"""

import re
import sys
from pathlib import Path

PLAFOND_OCTETS = 2_000_000
"""Un agrégat quotidien pèse quelques kilo-octets, un instantané mensuel
environ 150 Ko. Au-delà de deux méga-octets, quelque chose a mal tourné."""

# Une adresse, c'est une partie locale avant l'arobase. Un nom de domaine
# seul — le grain minimal que la page expose — ne doit pas déclencher l'alerte.
MOTIF_ADRESSE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def verifier(chemins):
    """Contrôle chaque fichier. Sort en erreur au premier problème."""
    for chemin in chemins:
        chemin = Path(chemin)
        taille = chemin.stat().st_size
        if taille > PLAFOND_OCTETS:
            raise SystemExit(
                f"REFUSÉ — taille : {chemin} pèse {taille} octets, "
                f"au-delà du plafond de {PLAFOND_OCTETS}."
            )
        trouve = MOTIF_ADRESSE.search(chemin.read_text(encoding="utf-8", errors="replace"))
        if trouve:
            raise SystemExit(
                f"REFUSÉ — adresse de messagerie détectée dans {chemin} : "
                f"{trouve.group()[:3]}… Aucun commit ne doit contenir de donnée nominative."
            )
    return len(chemins)


if __name__ == "__main__":
    nombre = verifier(sys.argv[1:])
    print(f"{nombre} fichier(s) contrôlé(s), aucun motif interdit.")
