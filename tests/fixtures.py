"""Fabrique d'extractions de test, au format réel de l'ANS.

Séparateur `|`, 31 colonnes, une ligne d'en-tête. Seules les colonnes 1
(type de BAL) et 2 (adresse) portent de l'information utile à l'outil ;
les 29 autres sont remplies à blanc.
"""

COLONNES = [
    "Type de BAL", "Adresse BAL", "Type Identifiant PP", "Identifiant PP",
    "Identification nationale PP", "Type identifiant structure",
    "Identification Structure", "Service de rattachement", "Civilité d'exercice",
    "Nom d'exercice", "Prénom d'exercice", "Catégorie profession",
    "Libellé de catégorie profession", "Code Profession", "Libellé Profession",
    "Code savoir-faire", "Libellé savoir-faire", "Dématérialisation",
    "Raison Sociale structure BAL", "Enseigne commerciale structure BAL",
    "L2COMPLEMENTLOCALISATION structure BAL", "L3COMPLEMENTDISTRIBUTION structure BAL",
    "L4NUMEROVOIE structure BAL", "L4COMPLEMENTNUMEROVOIE structure BAL",
    "NL4TYPEVOIE structure BAL", "L4LIBELLEVOIE structure BAL",
    "L5LIEUDITMENTION structure BAL", "L6LIGNEACHEMINEMENT structure BAL",
    "Code postal structure BAL", "Département structure BAL", "Pays structure BAL",
]


def extraction(*bal, entete=True):
    """Construit une extraction depuis des couples (type, adresse).

    Une chaîne au lieu d'un couple est insérée telle quelle, ce qui permet
    de fabriquer des lignes malformées.
    """
    lignes = ["|".join(COLONNES)] if entete else []
    for item in bal:
        if isinstance(item, str):
            lignes.append(item)
        else:
            type_bal, adresse = item
            champs = [""] * len(COLONNES)
            champs[0], champs[1] = type_bal, adresse
            lignes.append("|".join(champs))
    return ("\n".join(lignes) + "\n").encode("utf-8")
