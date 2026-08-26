"""État de référence : les empreintes de la veille, par domaine.

Ce fichier ne va JAMAIS dans le dépôt. Il vit dans le cache d'exécution
(§11 du brief). Il ne contient que des empreintes salées — le sel est un
secret de dépôt — et des noms de domaine, qui sont publics.

Format binaire, compact et sans ambiguïté : environ 4,3 Mo pour les
535 000 BAL observées, très en deçà des 10 Go du cache GitHub Actions.
"""

import gzip
import hashlib
import struct
from collections import defaultdict

from ingest.parse import TAILLE_EMPREINTE

SIGNATURE = b"MPBM\x02"
TAILLE_MARQUE_SEL = 8


def _marque_du_sel(sel):
    """Empreinte du sel lui-même, pour détecter une rotation. Ne le révèle pas."""
    return hashlib.blake2b(sel, digest_size=TAILLE_MARQUE_SEL).digest()
ENTETE_DOMAINE = struct.Struct("!HI")  # longueur du nom, nombre d'empreintes


def ecrire_etat(chemin, etat, sel):
    """Écrit `{domaine: set(empreintes)}` sous forme compacte et compressée."""
    with gzip.open(chemin, "wb") as sortie:
        sortie.write(SIGNATURE)
        sortie.write(_marque_du_sel(sel))
        for domaine, empreintes in sorted(etat.items()):
            nom = domaine.encode("utf-8")
            sortie.write(ENTETE_DOMAINE.pack(len(nom), len(empreintes)))
            sortie.write(nom)
            for empreinte in sorted(empreintes):
                sortie.write(empreinte)


def charger_etat(chemin, sel):
    """Relit un état. Renvoie None s'il est absent ou inutilisable.

    Le cache GitHub évince toute entrée non consultée pendant sept jours,
    et le sel peut avoir été renouvelé : ces deux cas sont nominaux, pas des
    erreurs. Le cycle repart alors de zéro et la journée est marquée
    indéterminée, jamais en anomalie.
    """
    try:
        with gzip.open(chemin, "rb") as entree:
            if entree.read(len(SIGNATURE)) != SIGNATURE:
                return None
            if entree.read(TAILLE_MARQUE_SEL) != _marque_du_sel(sel):
                return None  # sel renouvelé : les empreintes ne sont plus comparables
            etat = defaultdict(set)
            while True:
                entete = entree.read(ENTETE_DOMAINE.size)
                if not entete:
                    return dict(etat)
                taille_nom, nombre = ENTETE_DOMAINE.unpack(entete)
                domaine = entree.read(taille_nom).decode("utf-8")
                brut = entree.read(nombre * TAILLE_EMPREINTE)
                etat[domaine] = {
                    brut[i : i + TAILLE_EMPREINTE]
                    for i in range(0, len(brut), TAILLE_EMPREINTE)
                }
    except FileNotFoundError:
        return None
