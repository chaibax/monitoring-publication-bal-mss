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
