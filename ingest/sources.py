"""Accès aux points d'observation.

Trois sources, indépendantes par construction (§5 du brief) :

- l'extraction de l'ANS, source de contenu, en amont ;
- les métadonnées data.gouv, témoin du délai de diffusion ;
- l'API FHIR, signal de vie de l'annuaire.

Croiser deux d'entre elles localise le maillon en cause.
"""

import json
import os
import re
import shutil
import ssl
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CA_IGC_SANTE = Path(__file__).parent / "certificats" / "igc-sante.pem"
"""service.annuaire.sante.fr a pour racine IGC-Santé, absente des magasins
publics. Le certificat est fourni explicitement, jamais installé."""

URL_EXTRACTION_ANS = (
    "https://service.annuaire.sante.fr/annuaire-sante-webservices"
    "/V300/services/extraction/Extraction_Correspondance_MSSante"
)

# Le séparateur a changé avec la délégation à data.gouv en octobre 2026 :
# `…_202608261013.zip` servi par l'ANS, `…-202610161108.zip` sur le miroir.
MOTIF_HORODATAGE = re.compile(r"[-_](\d{12})\.zip")
MOTIF_NOM = re.compile(r"filename=([^;\s]+)")


def contexte_ans():
    """Contexte TLS pour le service d'extraction de l'ANS.

    Deux ancres, et non une seule. Le magasin du système d'abord, parce que
    depuis octobre 2026 le service répond en 302 vers data.gouv, dont le
    certificat relève d'une autorité publique : n'ancrer que l'IGC-Santé
    faisait échouer le saut, et c'est ce qui a mis l'outil à l'arrêt du
    10 au 16 octobre 2026. La racine IGC-Santé ensuite, pour le premier
    saut, que nulle autorité publique ne couvre.
    """
    contexte = ssl.create_default_context(cafile=os.environ.get("MONITORING_CA_BUNDLE"))
    contexte.load_verify_locations(cafile=str(CA_IGC_SANTE))
    return contexte


def contexte_public():
    """Contexte TLS pour les hôtes à autorité publique — data.gouv, l'API FHIR.

    Le magasin du système suffit sur un exécuteur correctement configuré.
    `MONITORING_CA_BUNDLE` permet d'en désigner un autre, ce dont ont besoin
    les installations Python de python.org sur macOS, livrées sans magasin.
    """
    return ssl.create_default_context(cafile=os.environ.get("MONITORING_CA_BUNDLE"))


def horodatage_depuis_nom_de_fichier(content_disposition):
    """Horodatage de génération porté par le nom de fichier de l'ANS.

    `Extraction_Correspondance_MSSante_202608261013.zip` -> 2026-08-26 10:13.
    L'heure est celle de l'ANS, heure de Paris.
    """
    trouve = MOTIF_HORODATAGE.search(content_disposition or "")
    if not trouve:
        raise ValueError(
            f"aucun horodatage exploitable dans : {content_disposition!r}"
        )
    return datetime.strptime(trouve.group(1), "%Y%m%d%H%M")


URL_METADONNEES_DATAGOUV = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "annuaire-sante-extraction-des-bal-mssante/"
)

URL_FHIR = "https://gateway.api.esante.gouv.fr/fhir/v2"

DELAI = 300


URL_ARCHIVE_DATAGOUV = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "annuaire-sante-extraction-des-bal-mssante-format-zip/"
)
"""Depuis octobre 2026, le service de l'ANS redirige vers ce jeu de données :
c'est le même fichier, au même horodatage, servi par la même redirection."""


@dataclass
class SondeANS:
    """Ce que la requête d'en-têtes apprend, sans transférer de contenu."""

    horodatage_generation: datetime
    taille_archive: int
    nom_fichier: str
    via: str = "service.annuaire.sante.fr"
    empreinte_sha1: str | None = None


def metadonnees_archive_datagouv(url=URL_ARCHIVE_DATAGOUV):
    """Métadonnées de l'archive sur le miroir : quelques kilo-octets.

    Le nom de fichier y porte encore l'horodatage de génération par l'ANS,
    et l'empreinte publiée permet de trancher la couche 1 sans télécharger.
    """
    with urllib.request.urlopen(url, timeout=DELAI, context=contexte_public()) as reponse:
        ressource = json.load(reponse)["resources"][0]
    extras = ressource.get("extras", {})
    return {
        "nom_fichier": ressource["url"].rsplit("/", 1)[-1],
        "taille": extras.get("analysis:content-length") or ressource.get("filesize"),
        "empreinte_sha1": extras.get("analysis:checksum"),
    }


DELAI_SONDE = 60
"""La sonde tourne dans un job plafonné à trois minutes : une source qui
pend ne doit pas consommer ce plafond avant que la suivante soit essayée."""


class SourceInjoignable(RuntimeError):
    """Aucune des voies n'a répondu. Le message les détaille toutes."""


def _essayer_dans_l_ordre(voies):
    """Première voie qui aboutit ; sinon une erreur qui les cite toutes.

    Toute exception compte comme un échec de la voie, sans liste fermée de
    types. Les deux pannes de l'outil venaient de là : en octobre une erreur
    de certificat, le 17 novembre 2026 une renégociation TLS refusée
    (`ssl.SSLError`, que `urllib` n'enveloppe pas en `URLError`). Chaque fois
    une erreur que la liste n'avait pas prévue a traversé la voie de repli
    et arrêté la collecte. On ne peut pas énumérer les façons de tomber
    d'un serveur tiers ; on peut refuser qu'une seule d'entre elles suffise.
    """
    echecs = []
    for nom, voie in voies:
        try:
            return voie()
        except Exception as motif:  # noqa: BLE001 - voir la docstring
            echecs.append(f"{nom} : {type(motif).__name__}: {motif}")
    raise SourceInjoignable(" | ".join(echecs))


def _sonder_miroir():
    miroir = metadonnees_archive_datagouv()
    return SondeANS(
        horodatage_generation=horodatage_depuis_nom_de_fichier(miroir["nom_fichier"]),
        taille_archive=int(miroir["taille"] or 0),
        nom_fichier=miroir["nom_fichier"],
        via="data.gouv.fr",
        empreinte_sha1=miroir["empreinte_sha1"],
    )


def _sonder_service_ans(url=URL_EXTRACTION_ANS):
    requete = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(requete, timeout=DELAI_SONDE, context=contexte_ans()) as reponse:
        disposition = reponse.headers.get("Content-Disposition", "")
        # data.gouv répond `Content-Disposition: attachment`, sans nom :
        # après redirection, l'horodatage ne subsiste que dans l'URL.
        trouve = MOTIF_NOM.search(disposition)
        nom = trouve.group(1) if trouve else reponse.url.rsplit("/", 1)[-1]
        return SondeANS(
            horodatage_generation=horodatage_depuis_nom_de_fichier(nom),
            taille_archive=int(reponse.headers.get("Content-Length", 0)),
            nom_fichier=nom,
        )


def sonder_source():
    """Couche 0 : la source produit-elle, et depuis quand ?

    Le miroir data.gouv d'abord. Depuis octobre 2026 l'ANS ne fait que
    rediriger vers lui, et depuis le 17 novembre 2026 son service exige un
    certificat client que l'outil n'a pas : c'est le même fichier, au même
    horodatage, par une voie de moins. Le service de l'ANS reste en second,
    pour le jour où la distribution changerait encore. Voir la décision 12.
    """
    return _essayer_dans_l_ordre([
        ("data.gouv.fr", _sonder_miroir),
        ("service.annuaire.sante.fr", _sonder_service_ans),
    ])


URL_TELECHARGEMENT_DATAGOUV = (
    "https://www.data.gouv.fr/api/1/datasets/r/ad782114-db10-4ad7-a295-28426acbca1e"
)
"""Lien stable vers l'archive sur le miroir, vers lequel l'ANS redirige."""


def _telecharger(adresse, contexte, destination):
    requete = urllib.request.Request(adresse)
    with urllib.request.urlopen(requete, timeout=DELAI, context=contexte) as reponse:
        with open(destination, "wb") as fichier:
            shutil.copyfileobj(reponse, fichier, length=1 << 20)
    return Path(destination)


def telecharger_archive(destination):
    """Rapatrie l'archive. Une vingtaine de méga-octets, quelques secondes.

    Même ordre que la sonde : le miroir, puis le service de l'ANS.
    """
    return _essayer_dans_l_ordre([
        ("data.gouv.fr",
         lambda: _telecharger(URL_TELECHARGEMENT_DATAGOUV, contexte_public(), destination)),
        ("service.annuaire.sante.fr",
         lambda: _telecharger(URL_EXTRACTION_ANS, contexte_ans(), destination)),
    ])


def lignes_de_l_archive(chemin):
    """Lignes du fichier unique contenu dans l'archive, en flux.

    Rien n'est décompressé sur disque ni chargé intégralement en mémoire.
    """
    with zipfile.ZipFile(chemin) as archive:
        membres = archive.namelist()
        if len(membres) != 1:
            raise ValueError(f"archive inattendue, {len(membres)} membres : {membres}")
        with archive.open(membres[0]) as flux:
            yield from flux


def sonder_datagouv(url=URL_METADONNEES_DATAGOUV):
    """Témoin de diffusion : quand le miroir a-t-il reçu le fichier ?"""
    with urllib.request.urlopen(url, timeout=DELAI, context=contexte_public()) as reponse:
        jeu = json.load(reponse)
    ressource = jeu["resources"][0]
    extras = ressource.get("extras", {})
    return {
        "depose_le": ressource.get("last_modified"),
        "empreinte_sha1": extras.get("analysis:checksum"),
        "taille": extras.get("analysis:content-length"),
        "url": ressource.get("url"),
    }


def signal_de_vie_annuaire(cle, debut, fin, ressource="PractitionerRole"):
    """Nombre de ressources de l'annuaire écrites sur la fenêtre donnée.

    Signal d'arrêt, pas mesure de volume : `_lastUpdated` marque une écriture
    technique, qu'une réindexation de masse ferait progresser sans qu'aucune
    BAL ait bougé (docs/00-sources.md, §5.3).
    """
    parametres = urllib.parse.urlencode(
        {
            "_lastUpdated": [f"ge{debut.isoformat()}", f"lt{fin.isoformat()}"],
            "_count": 1,
            "_total": "accurate",
        },
        doseq=True,
    )
    requete = urllib.request.Request(
        f"{URL_FHIR}/{ressource}?{parametres}", headers={"ESANTE-API-KEY": cle}
    )
    with urllib.request.urlopen(requete, timeout=DELAI, context=contexte_public()) as reponse:
        return json.load(reponse).get("total")
