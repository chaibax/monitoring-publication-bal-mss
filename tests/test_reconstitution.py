from datetime import date

from ingest.reconstitution import calendrier_depuis_evenements, interruptions


EVENEMENTS = [
    {"key": "dataset:resource:updated", "created_at": "2026-08-26T08:15:48+00:00"},
    {"key": "dataset:followed", "created_at": "2026-08-25T09:00:00+00:00"},
    {"key": "dataset:resource:updated", "created_at": "2026-08-23T03:00:00+00:00"},
]


def test_ne_retient_que_les_evenements_de_publication():
    """Un abonnement au jeu de données n'est pas une publication."""
    calendrier = calendrier_depuis_evenements(EVENEMENTS)

    assert set(calendrier) == {"2026-08-23", "2026-08-26"}


def test_repere_les_jours_sans_publication_entre_deux_observations():
    """Le fichier ne porte aucune date : un jour non observé est perdu.
    Encore faut-il savoir lesquels l'ont été."""
    trous = interruptions(calendrier_depuis_evenements(EVENEMENTS))

    assert trous == [(date(2026, 8, 24), date(2026, 8, 25))]


def test_un_calendrier_sans_trou_ne_produit_aucune_interruption():
    assert interruptions({"2026-08-25": "x", "2026-08-26": "y"}) == []


def test_le_calendrier_conserve_les_jours_deja_connus(fusionner=None):
    """Le rafraîchissement ne doit jamais faire disparaître un jour observé :
    l'API pourrait répondre partiellement, et un jour perdu se lirait comme
    une interruption qui n'a pas eu lieu."""
    from ingest.reconstitution import fusionner_calendriers

    ancien = {"2026-08-25": "2026-08-25T03:00:00+00:00"}
    nouveau = {"2026-08-26": "2026-08-26T08:15:00+00:00"}

    assert fusionner_calendriers(ancien, nouveau) == {
        "2026-08-25": "2026-08-25T03:00:00+00:00",
        "2026-08-26": "2026-08-26T08:15:00+00:00",
    }


def test_le_rafraichissement_prefere_l_horodatage_le_plus_tardif():
    from ingest.reconstitution import fusionner_calendriers

    fusion = fusionner_calendriers(
        {"2026-08-26": "2026-08-26T03:00:00+00:00"},
        {"2026-08-26": "2026-08-26T08:15:00+00:00"},
    )

    assert fusion["2026-08-26"] == "2026-08-26T08:15:00+00:00"
