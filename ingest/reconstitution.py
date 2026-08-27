"""Reconstitution du calendrier de publication, rétroactivement.

L'extraction ne porte aucune date : l'historique des volumes est perdu pour
qui n'observait pas. Mais data.gouv conserve la trace de chaque dépôt depuis
octobre 2025. On en tire le calendrier réel de la chaîne — quels jours elle
a produit, quels jours elle s'est tue — sans attendre plusieurs semaines
d'observation.

Portée : couche 0 seulement. Ces jours reconstitués n'ont ni volume de
créations ni ventilation par domaine, et ne doivent jamais être présentés
comme s'ils en avaient.
"""

import json
import urllib.request
from datetime import date, timedelta

EVENEMENT_PUBLICATION = "dataset:resource:updated"
JEU_DE_DONNEES = "6902546dfc27585fa038d104"
URL_ACTIVITE = "https://www.data.gouv.fr/api/1/activity/"


def calendrier_depuis_evenements(evenements):
    """Jour -> horodatage du dépôt le plus tardif observé ce jour-là."""
    calendrier = {}
    for evenement in evenements:
        if evenement.get("key") != EVENEMENT_PUBLICATION:
            continue
        horodatage = evenement["created_at"]
        jour = horodatage[:10]
        calendrier[jour] = max(calendrier.get(jour, ""), horodatage)
    return dict(sorted(calendrier.items()))


def interruptions(calendrier):
    """Séquences de jours sans publication, entre la première et la dernière.

    Les bornes du calendrier ne comptent pas : avant la première observation,
    l'outil ne sait rien, ce qui n'est pas la même chose qu'une interruption.
    """
    if len(calendrier) < 2:
        return []
    jours = sorted(date.fromisoformat(j) for j in calendrier)
    connus = set(jours)
    trous, debut, precedent = [], None, None
    courant = jours[0]
    while courant <= jours[-1]:
        if courant not in connus:
            if debut is None or (courant - precedent).days > 1:
                if debut is not None:
                    trous.append((debut, precedent))
                debut = courant
            precedent = courant
        courant += timedelta(days=1)
    if debut is not None:
        trous.append((debut, precedent))
    return trous


def fusionner_calendriers(ancien, nouveau):
    """Réunit deux calendriers, sans jamais perdre un jour déjà observé.

    L'API d'activité pourrait répondre partiellement ; un jour disparu du
    calendrier se lirait comme une interruption qui n'a pas eu lieu.
    """
    fusion = dict(ancien)
    for jour, horodatage in nouveau.items():
        fusion[jour] = max(fusion.get(jour, ""), horodatage)
    return dict(sorted(fusion.items()))


def telecharger_evenements(contexte=None, jeu=JEU_DE_DONNEES):
    """Historique complet des dépôts, en suivant la pagination."""
    evenements = []
    url = f"{URL_ACTIVITE}?related_to={jeu}&page_size=100"
    while url:
        with urllib.request.urlopen(url, timeout=120, context=contexte) as reponse:
            page = json.load(reponse)
        evenements += page["data"]
        url = page.get("next_page")
    return evenements
