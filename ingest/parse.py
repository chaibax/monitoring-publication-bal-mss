"""Lecture en flux d'une extraction des BAL MSSanté.

Le fichier ne porte ni date ni identifiant technique de BAL : l'adresse est
la seule clé. Elle ne sort jamais d'ici en clair — seule son empreinte salée
est conservée, et le sel est un secret de dépôt (voir docs/00-sources.md).
"""

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field

TAILLE_EMPREINTE = 8
"""Huit octets suffisent : sur 5 x 10^5 adresses, la probabilité de collision
est de l'ordre de 10^-6, très en deçà du bruit que l'outil cherche à mesurer."""


def empreinte_adresse(adresse, sel):
    """Empreinte salée et tronquée d'une adresse. Le sel est un secret."""
    return hashlib.blake2b(adresse, digest_size=TAILLE_EMPREINTE, key=sel).digest()


@dataclass
class Observation:
    """Ce qu'une lecture d'extraction produit, agrégats seuls.

    Aucun champ ne contient d'adresse, de nom ni d'identifiant individuel.
    """

    empreinte_fichier: str = ""
    lignes_lues: int = 0
    lignes_ignorees: int = 0
    par_type: dict[str, int] = field(default_factory=dict)
    empreintes_par_domaine: dict[str, set[bytes]] = field(default_factory=dict)

    @property
    def total_bal(self):
        return sum(len(e) for e in self.empreintes_par_domaine.values())

    @property
    def par_domaine(self):
        return {d: len(e) for d, e in self.empreintes_par_domaine.items()}

    @property
    def empreintes(self):
        """Toutes les empreintes, tous domaines confondus."""
        return set().union(set(), *self.empreintes_par_domaine.values())


def lire_extraction(flux, sel):
    """Lit une extraction et en tire les agrégats.

    `flux` est un itérable de lignes binaires — un fichier ouvert en binaire,
    un membre d'archive ZIP — ou un objet `bytes`. La lecture est en flux :
    le fichier n'est jamais chargé intégralement en mémoire.
    """
    if isinstance(flux, (bytes, bytearray)):
        flux = flux.splitlines(keepends=True)

    condensat = hashlib.sha256()
    par_type = Counter()
    empreintes_par_domaine = defaultdict(set)
    vues = set()
    lignes_lues = 0
    lignes_ignorees = 0

    for numero, ligne in enumerate(flux):
        condensat.update(ligne)
        if numero == 0:  # en-tête
            continue
        lignes_lues += 1

        champs = ligne.split(b"|", 2)
        if len(champs) < 2:
            lignes_ignorees += 1
            continue
        adresse = champs[1].strip().lower()
        _, arobase, domaine = adresse.partition(b"@")
        if not arobase or not domaine:
            lignes_ignorees += 1
            continue

        # Une même adresse peut figurer sur plusieurs lignes, une par
        # rattachement : 169 cas sur l'extraction du 25/08/2026.
        if adresse in vues:
            continue
        vues.add(adresse)

        nom_domaine = domaine.decode("utf-8")
        empreintes_par_domaine[nom_domaine].add(empreinte_adresse(adresse, sel))
        par_type[champs[0].strip().decode("utf-8")] += 1

    return Observation(
        empreinte_fichier=condensat.hexdigest(),
        lignes_lues=lignes_lues,
        lignes_ignorees=lignes_ignorees,
        par_type=dict(par_type),
        empreintes_par_domaine=dict(empreintes_par_domaine),
    )
