import ssl
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


MIROIR = {
    "nom_fichier": "extraction-correspondance-mssante-202610161108.zip",
    "taille": 21702416,
    "empreinte_sha1": "e8f35a8e",
}


def test_la_sonde_interroge_d_abord_le_miroir(monkeypatch):
    """L'ANS ne fait plus que rediriger vers data.gouv : le miroir est la
    voie directe, et le service de l'ANS n'est même pas sollicité."""
    from ingest import sources

    def interdit(*a, **k):
        raise AssertionError("le service de l'ANS ne doit pas être sollicité")

    monkeypatch.setattr(sources, "metadonnees_archive_datagouv", lambda: MIROIR)
    monkeypatch.setattr(sources, "_sonder_service_ans", interdit)

    sonde = sources.sonder_source()

    assert sonde.via == "data.gouv.fr"
    assert sonde.horodatage_generation.isoformat() == "2026-10-16T11:08:00"
    assert sonde.taille_archive == 21702416


@pytest.mark.parametrize("panne", [
    urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None),
    ssl.SSLError(1, "[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure"),
    ConnectionResetError(54, "Connection reset by peer"),
    KeyError("resources"),
])
def test_toute_panne_du_miroir_bascule_sur_le_service_de_l_ans(monkeypatch, panne):
    """Aucune liste fermée d'exceptions. Le 17 novembre 2026, une
    `ssl.SSLError` — que `urllib` n'enveloppe pas en `URLError` — a traversé
    la voie de repli et arrêté la collecte huit jours."""
    from ingest import sources

    def tombe():
        raise panne

    monkeypatch.setattr(sources, "metadonnees_archive_datagouv", tombe)
    monkeypatch.setattr(sources.urllib.request, "urlopen", lambda *a, **k: _ReponseFactice(
        "https://static.data.gouv.fr/x/extraction-correspondance-mssante-202610161108.zip",
        {"Content-Length": "21702416"},
    ))

    sonde = sources.sonder_source()

    assert sonde.via == "service.annuaire.sante.fr"
    assert sonde.horodatage_generation.isoformat() == "2026-10-16T11:08:00"


def test_la_sonde_echoue_franchement_quand_toutes_les_voies_tombent(monkeypatch):
    """Si rien ne répond, l'erreur cite chaque voie et son motif : c'est ce
    que lira la personne alertée."""
    from ingest import sources

    def tombe(*a, **k):
        raise ssl.SSLError(1, "handshake failure")

    monkeypatch.setattr(sources, "metadonnees_archive_datagouv", tombe)
    monkeypatch.setattr(sources.urllib.request, "urlopen", tombe)

    with pytest.raises(sources.SourceInjoignable) as erreur:
        sources.sonder_source()

    assert "data.gouv.fr" in str(erreur.value)
    assert "service.annuaire.sante.fr" in str(erreur.value)


def test_le_telechargement_bascule_sur_l_ans_si_le_miroir_tombe(monkeypatch, tmp_path):
    from ingest import sources

    appels = []

    def telecharger(adresse, contexte, destination):
        appels.append(adresse)
        if adresse == sources.URL_TELECHARGEMENT_DATAGOUV:
            raise ssl.SSLError(1, "handshake failure")
        return destination

    monkeypatch.setattr(sources, "_telecharger", telecharger)

    sources.telecharger_archive(tmp_path / "a.zip")

    assert appels == [sources.URL_TELECHARGEMENT_DATAGOUV, sources.URL_EXTRACTION_ANS]
