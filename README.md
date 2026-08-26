# Publication des BAL MSSanté dans l'Annuaire Santé — suivi quotidien

Observatoire automatisé de la chaîne de publication des boîtes aux lettres
MSSanté dans l'Annuaire Santé. Il détecte et date les ruptures, et distingue
une panne globale du système d'information d'une défaillance limitée à
certains domaines de messagerie.

**L'outil décrit ce qu'il observe. Il ne qualifie aucune responsabilité.**

## Ce qu'il publie

Pour chaque jour, le nombre d'adresses nouvellement publiées dans l'Annuaire
Santé, au niveau national et par domaine de messagerie. Des dénombrements,
pas des verdicts : un opérateur voit son propre chiffre, voit celui des
autres, et tire lui-même sa conclusion. C'est le point de comparaison qui
lui manque aujourd'hui.

Les seules qualifications affichées portent sur la chaîne nationale et ses
maillons, jamais sur un domaine pris isolément.

## Sources

| Source | Rôle | Accès |
|---|---|---|
| [Extraction MSSanté de l'ANS](https://annuaire.sante.fr/web/site-pro/extractions-mss) | contenu, en amont | libre |
| [Miroir data.gouv.fr](https://www.data.gouv.fr/datasets/annuaire-sante-extraction-des-bal-mssante) | témoin du délai de diffusion | libre |
| [API FHIR Annuaire Santé](https://gateway.api.esante.gouv.fr/fhir/v2) | signal de vie de l'annuaire | clé publique gratuite |

Leur intérêt vient de leur indépendance : croiser deux sources localise le
maillon en cause. La méthode, les limites connues et les mesures qui ont
fondé les choix techniques sont dans [`docs/00-sources.md`](docs/00-sources.md) ;
les décisions et leurs motifs dans [`docs/journal.md`](docs/journal.md).

## Données personnelles

Les extractions contiennent des données relatives à des professionnels de
santé. Le principe de minimisation s'applique sans exception :

- aucun enregistrement nominatif n'est jamais conservé, seuls des agrégats ;
- les différences se calculent sur des **empreintes salées** des adresses,
  jamais sur les adresses ; le sel est un secret de dépôt ;
- ces empreintes vivent dans le cache d'exécution, jamais dans Git ;
- le grain minimal exposé est le **domaine de messagerie**.

## Exécution

```bash
export MONITORING_SEL="…"          # secret de dépôt, jamais de valeur par défaut
python -m ingest.cycle sonde       # couche 0, quelques kilo-octets
python -m ingest.cycle traitement  # cycle complet, 20 Mo
```

Tests : `python -m pytest`

## Automatisation

| Tâche | Cadence | Rôle |
|---|---|---|
| `Supervision` | 03:10, 07:10, 11:10, 15:10, 19:10 UTC | sonde les en-têtes, traite si la source a bougé, publie et déploie |
| `Vigie de l'outil` | 09:40 UTC | échoue si plus aucun agrégat depuis 48 h |

Secrets et variables attendus dans le dépôt :

| Nom | Type | Nécessaire à |
|---|---|---|
| `MONITORING_SEL` | secret | empreintes salées des adresses |
| `NETLIFY_AUTH_TOKEN` | secret | redéploiement du site |
| `NETLIFY_SITE_ID` | variable | redéploiement du site |
| `SLACK_WEBHOOK` | secret, facultatif | alerte de la vigie |

Sans `NETLIFY_AUTH_TOKEN`, les agrégats sont publiés dans Git mais le site
n'est pas redéployé ; la tâche le signale par un avertissement.

## Licence

Code sous licence MIT. Données sources sous
[Licence Ouverte v2](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).
