import urllib.error

import pytest

from ingest.sources import horodatage_depuis_nom_de_fichier


def test_lit_l_horodatage_de_generation_dans_le_nom_de_fichier():
    """La réponse d'en-têtes de l'ANS porte l'horodatage de génération :
    c'est la couche 0, obtenue sans transférer un octet de contenu."""
    entete = "attachment; filename=Extraction_Correspondance_MSSante_202608261013.zip"

    assert horodatage_depuis_nom_de_fichier(entete).isoformat() == "2026-08-26T10:13:00"


def test_refuse_un_en_tete_sans_horodatage_exploitable():
    """Mieux vaut une erreur franche qu'un horodatage inventé : c'est lui
    qui fait foi pour toute la chaîne de détection."""
    with pytest.raises(ValueError):
        horodatage_depuis_nom_de_fichier("attachment; filename=extraction.zip")


def test_lit_l_horodatage_dans_une_url_finale_de_redirection():
    """Depuis octobre 2026, le service de l'ANS redirige vers data.gouv, dont
    la réponse ne porte plus de nom dans Content-Disposition. L'horodatage de
    génération ne subsiste que dans l'URL finale — et le séparateur y est un
    tiret, non plus un souligné."""
    url = ("https://static.data.gouv.fr/resources/"
           "annuaire-sante-extraction-des-bal-mssante-format-zip/20261016-091008/"
           "extraction-correspondance-mssante-202610161108.zip")

    assert horodatage_depuis_nom_de_fichier(url).isoformat() == "2026-10-16T11:08:00"


def test_lit_encore_l_ancien_nom_a_souligne():
    """L'ANS a pu servir directement le fichier : le format historique reste
    accepté, pour que rejouer une archive ancienne reste possible."""
    entete = "attachment; filename=Extraction_Correspondance_MSSante_202608261013.zip"

    assert horodatage_depuis_nom_de_fichier(entete).isoformat() == "2026-08-26T10:13:00"


class _ReponseFactice:
    def __init__(self, url, entetes):
        self.url, self.headers = url, entetes
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_la_sonde_bascule_sur_le_miroir_si_le_service_ans_refuse(monkeypatch):
    """L'ANS limite le débit de son service et répond 429. Un refus passager
    ne doit pas interrompre la supervision : le fichier est de toute façon
    distribué par data.gouv, vers qui l'ANS redirige lui-même."""
    from ingest import sources

    def refuse(*a, **k):
        raise urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(sources.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(sources, "metadonnees_archive_datagouv", lambda: {
        "nom_fichier": "extraction-correspondance-mssante-202610161108.zip",
        "taille": 21702416,
        "empreinte_sha1": "e8f35a8e",
    })

    sonde = sources.sonder_ans()

    assert sonde.horodatage_generation.isoformat() == "2026-10-16T11:08:00"
    assert sonde.taille_archive == 21702416
    assert sonde.via == "data.gouv.fr"


def test_la_sonde_privilegie_le_service_de_l_ans_quand_il_repond(monkeypatch):
    from ingest import sources

    monkeypatch.setattr(sources.urllib.request, "urlopen", lambda *a, **k: _ReponseFactice(
        "https://static.data.gouv.fr/x/extraction-correspondance-mssante-202610161108.zip",
        {"Content-Length": "21702416"},
    ))

    sonde = sources.sonder_ans()

    assert sonde.via == "service.annuaire.sante.fr"
    assert sonde.horodatage_generation.isoformat() == "2026-10-16T11:08:00"
