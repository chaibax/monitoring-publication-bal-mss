"""Couche 3 — absence de publication, par domaine.

Ce module ne produit rien qui soit affiché tel quel. La page publie des
dénombrements ; la détection statistique alimente le statut national, le
journal des incidents et les notifications internes (§15 du brief).

Sous une hypothèse de Poisson d'intensité lambda, la probabilité d'observer
zéro création vaut exp(-lambda). Le signal est retenu sous 1 %, soit une
intensité supérieure à environ 4,6 créations par jour. En deçà, l'absence
de création n'est pas informative.
"""

from math import exp, log
from statistics import median

from ingest.domaines import ACTIF

PROBABILITE_SIGNIFICATIVE = 0.01
SEUIL_INTENSITE = -log(PROBABILITE_SIGNIFICATIVE)  # ~4,605


def intensite_reference(occurrences):
    """Médiane des créations sur les occurrences du même jour de semaine.

    Les occurrences manquantes — jours sans observation — sont écartées
    plutôt que comptées comme des zéros : une panne de l'outil ne doit pas
    abaisser la référence et masquer une panne réelle le lendemain.
    """
    connues = [n for n in occurrences if n is not None]
    if not connues:
        return 0.0
    return float(median(connues))


def probabilite_zero(intensite):
    """Probabilité d'observer aucune création à cette intensité."""
    return exp(-intensite)


def signal_absence(intensite, creations, etat):
    """Vrai si l'absence de création est statistiquement significative.

    Un domaine en extinction ou retiré est exclu : son absence de créations
    est déjà expliquée par sa sortie de l'extraction (décision 4).
    """
    if etat != ACTIF:
        return False
    if creations > 0:
        return False
    return probabilite_zero(intensite) < PROBABILITE_SIGNIFICATIVE
