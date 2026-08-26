"""Écart entre deux observations successives.

Les créations et les suppressions se calculent par différence d'ensembles,
jamais par écart de total : entre le 11/06 et le 25/08/2026, un solde de
-10 363 masquait 61 875 mouvements réels.
"""

from dataclasses import dataclass


@dataclass
class EcartDomaine:
    creations: int
    suppressions: int
    total_bal: int


@dataclass
class Ecart:
    par_domaine: dict[str, EcartDomaine]

    @property
    def national(self):
        return EcartDomaine(
            creations=sum(d.creations for d in self.par_domaine.values()),
            suppressions=sum(d.suppressions for d in self.par_domaine.values()),
            total_bal=sum(d.total_bal for d in self.par_domaine.values()),
        )


def comparer(etat_veille, etat_jour):
    """Compare deux états `{domaine: set(empreintes)}`."""
    par_domaine = {}
    for domaine in etat_veille.keys() | etat_jour.keys():
        empreintes = etat_jour.get(domaine, set())
        hier = etat_veille.get(domaine, set())
        par_domaine[domaine] = EcartDomaine(
            creations=len(empreintes - hier),
            suppressions=len(hier - empreintes),
            total_bal=len(empreintes),
        )
    return Ecart(par_domaine=par_domaine)
