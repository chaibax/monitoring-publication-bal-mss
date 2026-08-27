import json
from datetime import date

from ingest import cycle


def ecrire(dossier, jour, empreinte):
    (dossier / f"{jour}.json").write_text(json.dumps({
        "date": jour, "source_fingerprint": empreinte, "statut": "nominal",
    }))


def test_la_reference_est_le_dernier_jour_anterieur(tmp_path, monkeypatch):
    monkeypatch.setattr(cycle, "DOSSIER_AGREGATS", tmp_path)
    ecrire(tmp_path, "2026-08-24", "avant-hier")
    ecrire(tmp_path, "2026-08-25", "hier")

    assert cycle.agregat_precedent(date(2026, 8, 26))["source_fingerprint"] == "hier"


def test_rejouer_un_jour_deja_traite_ne_le_compare_pas_a_lui_meme(tmp_path, monkeypatch):
    """Sans cela, relancer le traitement sur la même journée comparerait le
    fichier à sa propre empreinte : la couche 1 conclurait à une republication
    à l'identique et la page afficherait de la pluie sur une chaîne saine."""
    monkeypatch.setattr(cycle, "DOSSIER_AGREGATS", tmp_path)
    ecrire(tmp_path, "2026-08-25", "hier")
    ecrire(tmp_path, "2026-08-26", "aujourd-hui")

    assert cycle.agregat_precedent(date(2026, 8, 26))["source_fingerprint"] == "hier"


def test_sans_aucun_agregat_anterieur_il_n_y_a_pas_de_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(cycle, "DOSSIER_AGREGATS", tmp_path)

    assert cycle.agregat_precedent(date(2026, 8, 26)) is None


def test_un_etat_du_jour_meme_ne_sert_pas_de_reference(tmp_path, monkeypatch):
    """Rejouer un cycle sur la même source comparerait l'observation à
    elle-même : zéro mouvement, et l'outil annoncerait « aucune adresse
    publiée » sans avoir rien mesuré. La journée doit rester indéterminée."""
    monkeypatch.setattr(cycle, "DOSSIER_AGREGATS", tmp_path)

    assert cycle.etat_de_reference(date(2026, 8, 26), (date(2026, 8, 26), {"a": set()})) is None
    assert cycle.etat_de_reference(date(2026, 8, 26), (date(2026, 8, 25), {"a": set()})) == {"a": set()}
    assert cycle.etat_de_reference(date(2026, 8, 26), None) is None
