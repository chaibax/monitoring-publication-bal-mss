"""Un cycle de supervision, en deux commandes.

    python -m ingest.cycle sonde        couche 0, quelques kilo-octets
    python -m ingest.cycle traitement   cycle complet, 20 Mo

La sonde tourne toutes les quatre heures ; le traitement n'est déclenché
que si l'horodatage de génération a changé. En rythme nominal, cela fait
un traitement lourd par jour au lieu de cinq, et autant de charge en moins
sur les serveurs de l'ANS.

L'heure d'exécution n'est jamais l'horodatage de référence : c'est celui
du fichier source qui fait foi.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from ingest.agregat import agregat_quotidien, delai_diffusion, instantane_totaux
from ingest.etat import charger_etat, ecrire_etat
from ingest.parse import lire_extraction
from ingest.sources import (
    lignes_de_l_archive,
    sonder_ans,
    sonder_datagouv,
    telecharger_ans,
)

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_AGREGATS = RACINE / "data" / "daily"
DOSSIER_INSTANTANES = RACINE / "data" / "snapshots"
CHEMIN_ETAT = Path(os.environ.get("MONITORING_ETAT", RACINE / ".cache" / "etat.bin"))


def sel():
    """Sel cryptographique, secret de dépôt. Jamais de valeur par défaut."""
    valeur = os.environ.get("MONITORING_SEL")
    if not valeur:
        raise SystemExit(
            "MONITORING_SEL est absent. Sans sel secret, une empreinte "
            "d'adresse professionnelle est réidentifiable par force brute."
        )
    return valeur.encode("utf-8")


def dernier_agregat():
    """Le plus récent enregistrement quotidien déjà produit, s'il existe."""
    connus = sorted(DOSSIER_AGREGATS.glob("*.json"))
    return json.loads(connus[-1].read_text()) if connus else None


def sonde():
    """Couche 0 : la source produit-elle, et est-ce nouveau ?"""
    ans = sonder_ans()
    precedent = dernier_agregat()
    connu = precedent["source_timestamp"] if precedent else None
    horodatage = ans.horodatage_generation.isoformat()

    return {
        "horodatage_generation": horodatage,
        "taille_archive": ans.taille_archive,
        "nom_fichier": ans.nom_fichier,
        "dernier_traite": connu,
        "traitement_requis": horodatage != connu,
    }


def traitement():
    """Cycle complet : télécharger, lire, comparer, écrire."""
    ans = sonder_ans()
    jour = ans.horodatage_generation.date()

    with tempfile.TemporaryDirectory() as travail:
        archive = telecharger_ans(Path(travail) / ans.nom_fichier)
        observation = lire_extraction(lignes_de_l_archive(archive), sel=sel())

    precedent = dernier_agregat()
    enregistrement = agregat_quotidien(
        jour=jour,
        observation=observation,
        etat_veille=charger_etat(CHEMIN_ETAT, sel=sel()),
        empreinte_veille=precedent["source_fingerprint"] if precedent else None,
        horodatage_source=ans.horodatage_generation,
        diffusion=_diffusion(ans),
    )

    DOSSIER_AGREGATS.mkdir(parents=True, exist_ok=True)
    destination = DOSSIER_AGREGATS / f"{jour.isoformat()}.json"
    destination.write_text(
        json.dumps(enregistrement, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    )

    instantane = _ecrire_instantane_si_necessaire(jour, observation, enregistrement)

    CHEMIN_ETAT.parent.mkdir(parents=True, exist_ok=True)
    ecrire_etat(CHEMIN_ETAT, observation.empreintes_par_domaine, sel=sel())

    return {
        "ecrit": str(destination.relative_to(RACINE)),
        "instantane": instantane,
        "statut": enregistrement["statut"],
        "domaines_en_mouvement": len(enregistrement["domaines"]),
    }


def _ecrire_instantane_si_necessaire(jour, observation, enregistrement):
    """Point de resynchronisation : un par mois, plus un à chaque journée
    indéterminée, où les écarts ne sont pas calculables."""
    DOSSIER_INSTANTANES.mkdir(parents=True, exist_ok=True)
    du_mois = sorted(DOSSIER_INSTANTANES.glob(f"{jour:%Y-%m}-*.json"))
    if du_mois and enregistrement["statut"] != "indetermine":
        return None
    chemin = DOSSIER_INSTANTANES / f"{jour.isoformat()}.json"
    chemin.write_text(
        json.dumps(instantane_totaux(observation), ensure_ascii=False, sort_keys=True) + "\n"
    )
    return str(chemin.relative_to(RACINE))


def _diffusion(ans):
    """Délai entre génération par l'ANS et dépôt sur data.gouv.

    Deuxième cellule du bulletin météo. Une indisponibilité du miroir ne
    doit pas faire échouer le cycle : le maillon est alors non mesuré, ce
    qui n'est pas la même chose que mesuré favorable.
    """
    try:
        miroir = sonder_datagouv()
    except Exception as erreur:  # noqa: BLE001 - le miroir est secondaire
        return {"mesure": False, "motif": type(erreur).__name__}
    return {
        "mesure": True,
        "genere_le": ans.horodatage_generation.isoformat(),
        "depose_le": miroir["depose_le"],
        "delai_secondes": delai_diffusion(ans.horodatage_generation, miroir["depose_le"]),
        "empreinte_miroir": miroir["empreinte_sha1"],
    }


def main(arguments=None):
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("commande", choices=["sonde", "traitement"])
    choix = analyseur.parse_args(arguments)
    resultat = sonde() if choix.commande == "sonde" else traitement()
    json.dump(resultat, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
