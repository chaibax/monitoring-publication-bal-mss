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
