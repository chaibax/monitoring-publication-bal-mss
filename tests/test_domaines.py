from ingest.domaines import ACTIF, EN_EXTINCTION, RETIRE, etat_domaine


def test_un_domaine_au_volume_stable_est_actif():
    assert etat_domaine([120, 121, 119, 122]) == ACTIF


def test_un_domaine_sans_bal_sur_deux_observations_est_retire():
    """Décision 4 : deux observations, pour ne pas qualifier de retrait
    un fichier tronqué ou un cycle défaillant."""
    assert etat_domaine([40, 40, 0, 0]) == RETIRE


def test_un_seul_jour_a_zero_ne_suffit_pas_a_qualifier_un_retrait():
    assert etat_domaine([40, 40, 40, 0]) != RETIRE


def test_un_domaine_qui_perd_l_essentiel_de_son_volume_est_en_extinction():
    """Seuil de 80 % de la médiane des trente derniers jours."""
    assert etat_domaine([100, 100, 100, 15]) == EN_EXTINCTION


def test_une_baisse_ordinaire_ne_declenche_pas_l_extinction():
    assert etat_domaine([100, 100, 100, 85]) == ACTIF
