"""État d'un domaine de messagerie — décision 4 de docs/journal.md.

Un domaine qui sort de l'extraction n'est pas un domaine qui cesse de
publier. Le discriminant est le volume total, jamais les créations : un
`total_bal` stable avec zéro création, c'est un domaine qui publie et ne
crée rien ; un `total_bal` qui s'effondre, c'est un domaine qui s'en va.

Ces états sont internes. Ils ne sont jamais affichés comme un verdict :
ils servent à retirer du calcul d'anomalie les domaines dont l'absence de
créations est déjà expliquée.
"""

from statistics import median

ACTIF = "actif"
EN_EXTINCTION = "en_extinction"
RETIRE = "retire"

FENETRE = 30
"""Jours de référence pour la médiane de volume."""

SEUIL_EXTINCTION = 0.20
"""Un domaine tombé sous 20 % de sa médiane a perdu l'essentiel de son volume."""

OBSERVATIONS_AVANT_RETRAIT = 2
"""Deux observations à zéro, pour ne pas prendre un cycle défaillant pour un retrait."""


def etat_domaine(historique_total_bal):
    """État d'un domaine à partir de son historique de volume, chronologique.

    Le dernier élément est l'observation du jour.
    """
    if not historique_total_bal:
        return ACTIF

    recents = historique_total_bal[-OBSERVATIONS_AVANT_RETRAIT:]
    if len(recents) == OBSERVATIONS_AVANT_RETRAIT and not any(recents):
        return RETIRE

    reference = historique_total_bal[-FENETRE:-1] or historique_total_bal[-1:]
    mediane = median(reference)
    if mediane and historique_total_bal[-1] < SEUIL_EXTINCTION * mediane:
        return EN_EXTINCTION

    return ACTIF
