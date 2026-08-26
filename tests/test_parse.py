from ingest.parse import lire_extraction
from tests.fixtures import extraction

SEL = b"sel-de-test"


def test_compte_les_bal_par_domaine_de_messagerie():
    flux = extraction(
        ("PER", "a.b@medecin.mssante.fr"),
        ("PER", "c.d@medecin.mssante.fr"),
        ("ORG", "secretariat@chu-amiens.mssante.fr"),
    )

    obs = lire_extraction(flux, sel=SEL)

    assert obs.par_domaine == {
        "medecin.mssante.fr": 2,
        "chu-amiens.mssante.fr": 1,
    }


def test_une_adresse_repetee_sur_plusieurs_lignes_ne_compte_qu_une_fois():
    """Mesuré sur l'extraction du 25/08/2026 : 169 adresses apparaissent sur
    plusieurs lignes, une par rattachement. Sans déduplication le comptage
    serait faux de façon marginale mais permanente."""
    flux = extraction(
        ("PER", "a.b@medecin.mssante.fr"),
        ("PER", "a.b@medecin.mssante.fr"),
    )

    obs = lire_extraction(flux, sel=SEL)

    assert obs.par_domaine == {"medecin.mssante.fr": 1}
    assert obs.total_bal == 1
    assert obs.lignes_lues == 2


def test_les_adresses_ne_sortent_que_sous_forme_d_empreintes_salees():
    """Le dépôt est public : une empreinte non salée d'adresse professionnelle
    est triviale à réidentifier par force brute (§11 du brief)."""
    flux = extraction(("PER", "jean.dupont@medecin.mssante.fr"))

    avec_sel = lire_extraction(flux, sel=b"sel-a")
    avec_autre_sel = lire_extraction(flux, sel=b"sel-b")

    empreinte = next(iter(avec_sel.empreintes))
    assert len(avec_sel.empreintes) == 1
    assert b"jean.dupont" not in empreinte
    assert avec_sel.empreintes != avec_autre_sel.empreintes


def test_repartit_les_bal_par_type():
    """Deux types seulement dans cette source : PER et ORG. Pas d'applicative."""
    flux = extraction(
        ("PER", "a@medecin.mssante.fr"),
        ("PER", "b@medecin.mssante.fr"),
        ("ORG", "c@chu-amiens.mssante.fr"),
    )

    obs = lire_extraction(flux, sel=SEL)

    assert obs.par_type == {"PER": 2, "ORG": 1}


def test_ignore_les_lignes_inexploitables_et_les_denombre():
    """Aucune ligne malformée n'a été observée sur les trois extractions
    examinées, mais une ligne tronquée ne doit pas interrompre un cycle
    de supervision : elle est écartée et comptée."""
    flux = extraction(
        ("PER", "a@medecin.mssante.fr"),
        "PER",                          # ligne tronquée, pas de séparateur
        "ORG|",                         # adresse vide
        "ORG|pas-une-adresse",          # pas d'arobase
    )

    obs = lire_extraction(flux, sel=SEL)

    assert obs.total_bal == 1
    assert obs.lignes_ignorees == 3


def test_empreinte_du_fichier_identique_pour_un_contenu_identique():
    """Couche 1 : un fichier régénéré à l'identique signale un blocage en
    amont alors même que la production apparente fonctionne."""
    veille = extraction(("PER", "a@medecin.mssante.fr"))
    aujourdhui = extraction(("PER", "a@medecin.mssante.fr"))

    assert lire_extraction(veille, sel=SEL).empreinte_fichier == \
        lire_extraction(aujourdhui, sel=SEL).empreinte_fichier


def test_empreinte_du_fichier_differente_des_que_le_contenu_change():
    veille = extraction(("PER", "a@medecin.mssante.fr"))
    aujourdhui = extraction(
        ("PER", "a@medecin.mssante.fr"),
        ("PER", "b@medecin.mssante.fr"),
    )

    assert lire_extraction(veille, sel=SEL).empreinte_fichier != \
        lire_extraction(aujourdhui, sel=SEL).empreinte_fichier


def test_l_empreinte_du_fichier_ne_depend_pas_du_sel():
    """Elle porte sur la source, pas sur notre traitement : elle doit rester
    comparable d'une exécution à l'autre même si le sel est renouvelé."""
    flux = extraction(("PER", "a@medecin.mssante.fr"))

    assert lire_extraction(flux, sel=b"sel-a").empreinte_fichier == \
        lire_extraction(flux, sel=b"sel-b").empreinte_fichier


def test_les_empreintes_sont_rattachees_a_leur_domaine():
    """Les créations et suppressions se calculent par domaine. L'empreinte
    étant à sens unique, le domaine doit être conservé à côté d'elle."""
    flux = extraction(
        ("PER", "a@medecin.mssante.fr"),
        ("PER", "b@medecin.mssante.fr"),
        ("ORG", "c@chu-amiens.mssante.fr"),
    )

    obs = lire_extraction(flux, sel=SEL)

    assert set(obs.empreintes_par_domaine) == {"medecin.mssante.fr", "chu-amiens.mssante.fr"}
    assert len(obs.empreintes_par_domaine["medecin.mssante.fr"]) == 2
    assert len(obs.empreintes_par_domaine["chu-amiens.mssante.fr"]) == 1
    assert obs.empreintes == set().union(*obs.empreintes_par_domaine.values())
