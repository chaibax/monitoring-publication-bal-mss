from datetime import date

from ingest.etat import charger_etat, ecrire_etat


def e(*octets):
    return {bytes([n]) * 8 for n in octets}


def test_l_etat_relu_est_identique_a_l_etat_ecrit(tmp_path):
    """L'état de référence vit hors dépôt Git, dans le cache d'exécution.
    Un aller-retour infidèle fausserait toutes les différences du lendemain."""
    etat = {"medecin.mssante.fr": e(1, 2, 3), "chu-amiens.mssante.fr": e(4)}
    chemin = tmp_path / "etat.bin"

    ecrire_etat(chemin, etat, sel=b"sel", jour=date(2026, 8, 26))

    assert charger_etat(chemin, sel=b"sel")[1] == etat


def test_un_etat_absent_se_lit_comme_vide(tmp_path):
    """Le cache GitHub évince une entrée non consultée pendant sept jours.
    Au redémarrage, l'outil repart de zéro sans échouer."""
    assert charger_etat(tmp_path / "jamais-ecrit.bin", sel=b"sel") is None


def test_l_etat_ne_contient_aucune_adresse_en_clair(tmp_path):
    chemin = tmp_path / "etat.bin"

    ecrire_etat(chemin, {"medecin.mssante.fr": e(1)}, sel=b"sel", jour=date(2026, 8, 26))

    assert b"@" not in chemin.read_bytes()


def test_un_etat_ecrit_avec_un_autre_sel_est_refuse(tmp_path):
    """Renouveler le sel change toutes les empreintes. Sans ce garde-fou,
    la rotation d'un secret produirait 535 000 créations fantômes et un
    incident national parfaitement imaginaire."""
    chemin = tmp_path / "etat.bin"
    ecrire_etat(chemin, {"medecin.mssante.fr": e(1)}, sel=b"ancien-sel", jour=date(2026, 8, 26))

    assert charger_etat(chemin, sel=b"nouveau-sel") is None
    assert charger_etat(chemin, sel=b"ancien-sel")[1] == {"medecin.mssante.fr": e(1)}


def test_l_etat_porte_le_jour_qu_il_decrit(tmp_path):
    """Sans cela, rejouer un cycle sur la même source compare l'état à
    lui-même, obtient zéro mouvement, et l'outil annonce « aucune adresse
    publiée » alors qu'il n'a rien mesuré du tout."""
    from datetime import date

    chemin = tmp_path / "etat.bin"
    ecrire_etat(chemin, {"medecin.mssante.fr": e(1)}, sel=b"sel", jour=date(2026, 8, 26))

    jour, etat = charger_etat(chemin, sel=b"sel")

    assert jour == date(2026, 8, 26)
    assert etat == {"medecin.mssante.fr": e(1)}
