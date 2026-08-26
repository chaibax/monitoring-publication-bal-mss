from datetime import date, datetime

from ingest.agregat import agregat_quotidien
from ingest.parse import Observation

HORODATAGE = datetime(2026, 8, 26, 10, 13)


def obs(par_domaine, empreinte="abc123"):
    return Observation(
        empreinte_fichier=empreinte,
        lignes_lues=sum(len(v) for v in par_domaine.values()),
        par_type={"PER": sum(len(v) for v in par_domaine.values())},
        empreintes_par_domaine=par_domaine,
    )


def e(*octets):
    return {bytes([n]) * 8 for n in octets}


def test_sans_etat_de_la_veille_la_journee_est_indeterminee():
    """Critère d'acceptation n°7 : une absence de données de l'outil produit
    un brouillard, jamais une pluie. Le pire résultat possible serait qu'une
    panne de l'outil soit prise pour une panne de la chaîne MSSanté."""
    enr = agregat_quotidien(
        jour=date(2026, 8, 26),
        observation=obs({"medecin.mssante.fr": e(1, 2)}),
        etat_veille=None,
        empreinte_veille=None,
        horodatage_source=HORODATAGE,
    )

    assert enr["statut"] == "indetermine"
    assert enr["national"]["creations"] is None
    assert enr["national"]["suppressions"] is None
    assert enr["national"]["total_bal"] == 2


def test_avec_l_etat_de_la_veille_les_mouvements_sont_denombres():
    enr = agregat_quotidien(
        jour=date(2026, 8, 26),
        observation=obs({"medecin.mssante.fr": e(1, 2, 4)}),
        etat_veille={"medecin.mssante.fr": e(1, 2, 3)},
        empreinte_veille="differente",
        horodatage_source=HORODATAGE,
    )

    assert enr["statut"] == "nominal"
    assert enr["national"] == {"total_bal": 3, "creations": 1, "suppressions": 1}
    assert enr["domaines"]["medecin.mssante.fr"] == [3, 1, 1]  # total, créations, suppressions


def test_un_fichier_republie_a_l_identique_signale_une_interruption():
    """Couche 1 : un fichier régénéré mais identique signale un blocage en
    amont, alors même que la production apparente fonctionne."""
    enr = agregat_quotidien(
        jour=date(2026, 8, 26),
        observation=obs({"medecin.mssante.fr": e(1, 2)}, empreinte="figee"),
        etat_veille={"medecin.mssante.fr": e(1, 2)},
        empreinte_veille="figee",
        horodatage_source=HORODATAGE,
    )

    assert enr["statut"] == "interrompu"


def test_l_agregat_ne_contient_aucune_empreinte_ni_adresse():
    """Garde-fou §11 : le dépôt est public, une donnée commitée par erreur
    reste dans l'historique Git et devient indexable."""
    import json

    enr = agregat_quotidien(
        jour=date(2026, 8, 26),
        observation=obs({"medecin.mssante.fr": e(1, 2)}),
        etat_veille={"medecin.mssante.fr": e(1)},
        empreinte_veille="differente",
        horodatage_source=HORODATAGE,
    )

    serialise = json.dumps(enr)
    assert "@" not in serialise
    assert "0101010101010101" not in serialise


def test_seuls_les_domaines_ayant_bouge_figurent_dans_l_enregistrement():
    """Un enregistrement portant les 5 019 domaines pèse 497 Ko, soit 138 Mo
    par an dans un dépôt public dont l'historique est immuable. Les domaines
    sans mouvement n'apportent rien : leur total se reconstitue depuis le
    dernier instantané et le cumul des écarts."""
    enr = agregat_quotidien(
        jour=date(2026, 8, 26),
        observation=obs({"bouge.mssante.fr": e(1, 2), "stable.mssante.fr": e(9)}),
        etat_veille={"bouge.mssante.fr": e(1), "stable.mssante.fr": e(9)},
        empreinte_veille="differente",
        horodatage_source=HORODATAGE,
    )

    assert set(enr["domaines"]) == {"bouge.mssante.fr"}
    assert enr["domaines"]["bouge.mssante.fr"] == [2, 1, 0]


def test_une_journee_indeterminee_ne_porte_aucun_domaine():
    """Aucun écart n'est calculable : l'instantané des totaux fait foi."""
    enr = agregat_quotidien(
        jour=date(2026, 8, 26),
        observation=obs({"medecin.mssante.fr": e(1, 2)}),
        etat_veille=None,
        empreinte_veille=None,
        horodatage_source=HORODATAGE,
    )

    assert enr["domaines"] == {}
