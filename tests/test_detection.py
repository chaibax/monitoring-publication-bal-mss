from ingest.detection import SEUIL_INTENSITE, intensite_reference, signal_absence
from ingest.domaines import ACTIF, EN_EXTINCTION, RETIRE


def test_un_domaine_de_faible_intensite_ne_signale_jamais_une_journee_sans_creation():
    """Critère d'acceptation n°3. Sous une intensité de 4,6 créations par
    jour, la probabilité d'observer zéro dépasse 1 % : l'absence n'est pas
    informative. La médiane est ici de 2, cas majoritaire — 64 % des
    domaines comptent moins de dix BAL au total."""
    assert signal_absence(intensite=2.0, creations=0, etat=ACTIF) is False


def test_un_domaine_de_forte_intensite_sans_aucune_creation_est_signale():
    assert signal_absence(intensite=50.0, creations=0, etat=ACTIF) is True


def test_le_seuil_correspond_bien_a_une_probabilite_de_un_pour_cent():
    assert 4.5 < SEUIL_INTENSITE < 4.7


def test_une_creation_suffit_a_eteindre_le_signal():
    assert signal_absence(intensite=50.0, creations=1, etat=ACTIF) is False


def test_un_domaine_en_extinction_n_est_jamais_signale():
    """Décision 4, effet 1 : ses créations nulles sont déjà expliquées.
    Sans cette exclusion, la fermeture d'un EHPAD produirait un faux
    signal permanent."""
    assert signal_absence(intensite=50.0, creations=0, etat=EN_EXTINCTION) is False


def test_un_domaine_retire_n_est_jamais_signale():
    assert signal_absence(intensite=50.0, creations=0, etat=RETIRE) is False


def test_l_intensite_de_reference_est_la_mediane_du_meme_jour_de_semaine():
    """§8 du brief : huit dernières occurrences du même jour de semaine."""
    assert intensite_reference([10, 12, 11, 40, 9, 13, 12, 11]) == 11.5


def test_l_intensite_de_reference_ignore_les_occurrences_manquantes():
    assert intensite_reference([None, 12, None, 10]) == 11.0


def test_sans_historique_l_intensite_est_nulle():
    """Aucun historique : aucune alerte possible. L'outil se tait plutôt
    que de deviner."""
    assert intensite_reference([]) == 0.0
