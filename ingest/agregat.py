"""Enregistrement quotidien — le seul objet qui entre dans le dépôt.

Quelques kilo-octets par jour, versionnés sous `data/daily/AAAA-MM-JJ.json`.
L'historique est ainsi gratuit, auditable et rejouable.

Aucun champ ne contient d'adresse, de nom, d'identifiant individuel ni
d'empreinte. Le grain minimal exposé est le domaine de messagerie.
"""

from datetime import datetime, timezone

from ingest.diff import comparer

NOMINAL = "nominal"
INTERROMPU = "interrompu"
INDETERMINE = "indetermine"


def agregat_quotidien(
    jour,
    observation,
    etat_veille,
    empreinte_veille,
    horodatage_source,
    diffusion=None,
):
    """Construit l'enregistrement du jour.

    `etat_veille` à None — premier cycle, ou cache évincé après sept jours —
    donne une journée indéterminée : les mouvements sont inconnus, et
    l'inconnu ne doit jamais se lire comme une anomalie.
    """
    connait_la_veille = etat_veille is not None

    if not connait_la_veille:
        statut = INDETERMINE
        ecart = None
    elif empreinte_veille == observation.empreinte_fichier:
        # Couche 1 : fichier régénéré à l'identique.
        statut = INTERROMPU
        ecart = comparer(etat_veille, observation.empreintes_par_domaine)
    else:
        statut = NOMINAL
        ecart = comparer(etat_veille, observation.empreintes_par_domaine)

    # Seuls les domaines ayant bougé sont consignés : le total d'un domaine
    # immobile se reconstitue depuis le dernier instantané et le cumul des
    # écarts. Un enregistrement exhaustif pèserait 497 Ko par jour, soit
    # 138 Mo par an dans un dépôt public dont l'historique est immuable.
    domaines = {}
    if ecart:
        for domaine, mouvements in sorted(ecart.par_domaine.items()):
            if mouvements.creations or mouvements.suppressions:
                domaines[domaine] = [
                    mouvements.total_bal,
                    mouvements.creations,
                    mouvements.suppressions,
                ]

    return {
        "date": jour.isoformat(),
        "source_timestamp": horodatage_source.isoformat(),
        "source_fingerprint": observation.empreinte_fichier,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "statut": statut,
        "national": {
            "total_bal": observation.total_bal,
            "creations": ecart.national.creations if ecart else None,
            "suppressions": ecart.national.suppressions if ecart else None,
        },
        "par_type": observation.par_type,
        "lignes_lues": observation.lignes_lues,
        "lignes_ignorees": observation.lignes_ignorees,
        # Le fichier ne porte aucune date d'enregistrement et l'adresse est
        # la seule clé : une modification est indiscernable d'une suppression
        # suivie d'une création. Le champ prévu au §7 du brief reste vide.
        "modifications": None,
        "diffusion": diffusion,
        # domaine -> [total_bal, creations, suppressions]
        "domaines": domaines,
    }


def instantane_totaux(observation):
    """Photographie complète des volumes par domaine.

    Écrite au premier cycle de chaque mois et chaque fois qu'une journée est
    indéterminée. Elle sert de point de resynchronisation : instantané plus
    cumul des écarts quotidiens reconstitue n'importe quelle date, ce qui
    satisfait le critère d'acceptation n°5 sans conserver les archives brutes.
    """
    return dict(sorted(observation.par_domaine.items()))
