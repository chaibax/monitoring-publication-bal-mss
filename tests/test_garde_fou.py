import pytest

from ingest.garde_fou import PLAFOND_OCTETS, verifier


def test_refuse_un_fichier_contenant_une_adresse_de_messagerie(tmp_path):
    """Sur un dépôt public alimenté par un robot, une revue humaine ne suffit
    pas : une donnée commitée reste dans l'historique Git et devient indexable."""
    coupable = tmp_path / "2026-08-26.json"
    coupable.write_text('{"domaines": {"jean.dupont@medecin.mssante.fr": [1, 0, 0]}}')

    with pytest.raises(SystemExit) as sortie:
        verifier([coupable])

    assert "adresse" in str(sortie.value)


def test_refuse_un_fichier_qui_depasse_le_plafond(tmp_path):
    """Un agrégat quotidien pèse quelques kilo-octets. Un fichier volumineux
    signale qu'une extraction brute a été confondue avec un agrégat."""
    enorme = tmp_path / "2026-08-26.json"
    enorme.write_text("0" * (PLAFOND_OCTETS + 1))

    with pytest.raises(SystemExit) as sortie:
        verifier([enorme])

    assert "taille" in str(sortie.value)


def test_laisse_passer_un_agregat_normal(tmp_path):
    sain = tmp_path / "2026-08-26.json"
    sain.write_text('{"domaines": {"medecin.mssante.fr": [62151, 12, 3]}}')

    assert verifier([sain]) == 1


def test_un_nom_de_domaine_seul_n_est_pas_une_adresse(tmp_path):
    """Le grain minimal exposé est le domaine : il ne doit pas déclencher
    le garde-fou, sinon plus aucun agrégat ne passe."""
    sain = tmp_path / "instantane.json"
    sain.write_text('{"chu-amiens.mssante.fr": 678, "aura.mssante.fr": 62143}')

    assert verifier([sain]) == 1
