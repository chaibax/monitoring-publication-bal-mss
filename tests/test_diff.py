from ingest.diff import comparer


def e(*octets):
    """Empreintes de test, lisibles."""
    return {bytes([n]) * 8 for n in octets}


def test_un_solde_nul_peut_masquer_autant_de_creations_que_de_suppressions():
    """§8 du brief : le calcul doit être fait par différence d'ensembles,
    jamais à partir du seul écart de total. Vérifié ici sur le cas qui
    rendrait le total aveugle."""
    veille = {"medecin.mssante.fr": e(1, 2, 3)}
    jour = {"medecin.mssante.fr": e(1, 2, 4)}

    ecart = comparer(veille, jour)

    domaine = ecart.par_domaine["medecin.mssante.fr"]
    assert domaine.creations == 1
    assert domaine.suppressions == 1
    assert domaine.total_bal == 3


def test_un_domaine_disparu_reste_dans_l_ecart_avec_un_total_nul():
    """Décision 4 : un domaine qui sort de l'extraction doit être visible
    comme tel, sinon il disparaît silencieusement du suivi et l'outil ne
    peut plus distinguer un retrait d'une interruption de publication."""
    veille = {"ehpad-ferme.mssante.fr": e(1, 2)}
    jour = {}

    ecart = comparer(veille, jour)

    domaine = ecart.par_domaine["ehpad-ferme.mssante.fr"]
    assert domaine.total_bal == 0
    assert domaine.suppressions == 2
    assert domaine.creations == 0


def test_agrege_les_mouvements_au_niveau_national():
    veille = {"a.mssante.fr": e(1, 2), "b.mssante.fr": e(3)}
    jour = {"a.mssante.fr": e(1, 2, 4), "b.mssante.fr": set(), "c.mssante.fr": e(5)}

    ecart = comparer(veille, jour)

    assert ecart.national.creations == 2       # 4 sur a, 5 sur c
    assert ecart.national.suppressions == 1    # 3 sur b
    assert ecart.national.total_bal == 4
