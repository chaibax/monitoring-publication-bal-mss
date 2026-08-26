# Journal des décisions et des surprises

Consigne les décisions techniques et ce que les données ont démenti. Une entrée par décision, datée, avec le motif. Ce fichier n'est pas un compte rendu d'avancement : il n'enregistre que ce qui engage la suite.

---

## 26/08/2026 — Étape 0

### Décision 1 — La source de contenu est le webservice de l'ANS ; data.gouv est le témoin de diffusion

*Cette décision a été prise dans les deux sens le même jour. La première rédaction écartait le webservice de l'ANS ; une mesure complémentaire l'a renversée. Les deux états sont conservés ici, parce que le motif du renversement importe autant que la conclusion.*

**Première rédaction, écartant l'ANS.** La chaîne TLS de `service.annuaire.sante.fr` a pour racine **IGC-Santé**, absente des magasins de confiance publics : `curl` comme Python échouent en vérification depuis un poste standard, et un exécuteur GitHub échouerait de même. J'en avais conclu que le miroir data.gouv, servi derrière une autorité publique, était la seule voie raisonnable.

**Ce que la mesure complémentaire a montré.** Fournie explicitement en ancre de confiance, la racine IGC-Santé fait aboutir la connexion : en-têtes en HTTP 200, téléchargement complet en 1,9 s. Cette racine est un certificat **public**, valable jusqu'au **25 juin 2033**, versionnable dans le dépôt et passé au client sans jamais modifier le magasin du système. L'obstacle était réel mais franchissable, et il ne coûte ni secret, ni dépendance à l'environnement.

Une fois franchi, la source ANS est supérieure sur trois points que le miroir ne peut pas égaler :

- la réponse d'en-têtes porte `Content-Disposition: filename=Extraction_Correspondance_MSSante_202608261013.zip`, soit **l'horodatage de génération réel, sans transférer un octet de contenu** ;
- l'archive pèse **20 Mo** contre 89 Mo en clair, soit un facteur 4,4 ;
- elle est **en amont**, là où le miroir est un report.

**Ce que le miroir garde comme rôle.** Il ne disparaît pas du dispositif, il change de fonction. L'écart entre l'horodatage de génération ANS et l'horodatage de dépôt data.gouv **mesure le délai de diffusion** : deux minutes trente au 26/08/2026. Une source qui avance pendant que l'autre stagne localise la rupture sans ambiguïté. La deuxième cellule du bulletin météo, que le brief laissait non instrumentée en v1, devient donc alimentée dès la v1, pour une requête légère par cycle. data.gouv fournit en outre la mémoire du calendrier via l'API `activity`, que l'ANS n'expose nulle part, et une solution de repli en cas d'indisponibilité du webservice.

**Conséquence sur le modèle de données.** Le champ `source_timestamp` retrouve le sens que lui donnait le brief : **date et heure de génération par l'ANS**. La réserve inscrite en première rédaction est levée.

**Point à ne pas confondre.** L'extraction `Correspondance_MSSante` est en **libre accès** : la requête aboutit sans clé ni certificat client. Des droits d'accès étendus ne changent rien à ce fichier ; ils n'ouvriraient que des extractions en accès restreint, écartées pour préserver la reproductibilité par un tiers sur un dépôt public.

**Ce qui n'a pas changé : l'API FHIR n'est pas et ne sera pas la source quotidienne.** Mesuré : elle ne sait pas compter par domaine de messagerie — `mailbox-mss` ne répond qu'en égalité stricte, et le modificateur `:contains` donne des résultats incohérents. Reconstituer la vue par domaine y supposerait de parcourir plus de quatre millions de ressources chaque jour, ce qui pèserait sur les services de l'ANS pour un résultat moins bon que la lecture d'un fichier de 20 Mo. **L'API FHIR reste le signal de vie de l'annuaire, via `_lastUpdated`** — troisième point d'observation, irremplaçable dans ce rôle, inadapté à tout autre.

### Décision 2 — L'incident de référence est celui de l'été 2026

Le brief le datait de l'été 2025 ; c'était une erreur de millésime. L'interruption mesurée dans l'historique des publications court du **30 juillet au 8 août 2026**, dix jours.

Conséquence utile : le jeu de données de test du critère d'acceptation n°1 se construit sur un épisode réel vieux de trois semaines, et non sur un scénario reconstitué.

### Décision 3 — Les domaines sous 30 BAL sont regroupés en agrégat « autres »

Mesuré au 25/08/2026 sur 5 018 domaines : la médiane est de **4 BAL** et 64 % des domaines en comptent moins de dix. Le seuil de 30 sépare **1 001 domaines, qui portent 95,8 % du volume**, des 4 017 autres, qui en portent 4,2 %.

Le regroupement retire les deux tiers du bruit de la matrice sans rien retrancher de significatif, et évite d'exposer plusieurs milliers de très petits exploitants à une lecture erronée. Seuil à documenter dans la page méthode, avec ces chiffres.

### Décision 4 — Un retrait de domaine n'est pas une interruption de publication

**Le problème.** Sur 75 jours, 482 domaines ont disparu de l'extraction. Sans règle, chacun produirait une ligne de zéros indiscernable d'une panne, à demeure. Une matrice de supervision qui accuse en permanence des domaines qui n'existent plus est inutilisable.

**Le discriminant est le volume total du domaine, jamais ses créations.**

| Observation | Lecture |
|---|---|
| `total_bal` stable, `creations` à 0 | Le domaine publie toujours, il ne crée rien. Signal de publication éventuel. |
| `total_bal` s'effondre vers 0 | Le domaine sort de l'extraction. Ce n'est pas un signal de publication. |

**Trois états internes de domaine**, jamais affichés comme verdict :

- `actif` — `total_bal` supérieur à zéro, stable ou croissant ;
- `en_extinction` — `total_bal` a perdu au moins 80 % de sa médiane des trente derniers jours ;
- `retire` — `total_bal` nul sur au moins deux observations consécutives.

**Quatre effets, qui sont la décision proprement dite :**

1. Un domaine `en_extinction` ou `retire` est **exclu du calcul de Poisson de la couche 3**. Ses créations nulles sont expliquées ; elles ne peuvent plus ouvrir d'incident. Sans cette exclusion, la fermeture d'un seul EHPAD produirait un faux signal permanent.
2. Le journal des incidents reçoit un événement `retrait_domaine`, **distinct** de `interruption_publication` : périmètre d'un domaine, volume au dernier jour observé, **sans durée** — ce n'est pas un incident, c'est un fait.
3. Dans la matrice, la ligne d'un domaine retiré est rendue **hors périmètre** à compter de la date de retrait : même traitement graphique que les données manquantes, jamais une file de zéros. Idem avant la première apparition d'un domaine. La correspondance exigée au critère d'acceptation n°8 entre bande chronologique et histogramme s'étend donc à ce quatrième état.
4. Un retrait n'est **jamais qualifié**. Ni fermeture, ni migration, ni bascule en liste rouge. Le libellé public est « domaine plus présent dans l'extraction depuis le … ». Le ton reste celui du §14 du brief : l'outil décrit, il n'impute pas.

**Ce que la mesure dit du risque réel.** Sur les 482 domaines disparus, **6 seulement dépassaient 30 BAL**, le plus gros en comptant 44, et l'ensemble ne représente que **1 633 BAL**. Le seuil de la décision 3 absorbe donc l'essentiel du phénomène : à peine une poignée de cas atteindront la vue publiée sur un trimestre. La règle ci-dessus n'a pas besoin d'être sophistiquée, elle a besoin d'exister.

**Réserve à documenter dans la page méthode.** Un basculement collectif en liste rouge est **indiscernable** d'un retrait de domaine : dans les deux cas les adresses sortent de l'extraction. L'outil ne peut pas trancher et ne doit pas prétendre le faire.

**Renvoyé en v2.** La détection de migration — un domaine qui disparaît pendant qu'un autre apparaît avec la même population — est faisable en comparant les empreintes salées des parties locales des adresses, qui survivent généralement à un changement de domaine. Hors périmètre v1 : le gain est faible tant que les cas se comptent sur les doigts d'une main.

### Décision 5 — Deux jobs dans une tâche, plutôt que deux tâches distinctes

Le §6.1 du brief prévoyait deux workflows séparés. L'implémentation en retient
un seul, avec deux jobs enchaînés par `needs` et une condition.

Le motif du brief est respecté à la lettre — « et non un seul job lourd
répété » : la sonde interroge les en-têtes cinq fois par jour sans transférer
de contenu, et le traitement ne part que si l'horodatage de génération a
bougé, soit une fois par jour en rythme nominal. Deux jobs suffisent à cela,
et évitent le déclenchement croisé d'un workflow par un autre, qui exige un
jeton supplémentaire et rend le lien entre sonde et traitement invisible dans
l'historique d'exécution. Les plafonds de durée restent distincts, trois
minutes pour la sonde et quinze pour le traitement.

### Décision 6 — Le déploiement passe par un jeton, pas par un liage OAuth

Le site n'est pas relié au dépôt côté Netlify. C'est la tâche planifiée qui
appelle `netlify deploy` avec un jeton en secret de dépôt. Cela évite une
autorisation croisée entre GitHub et Netlify et garde tout le déclenchement
dans le dépôt, donc lisible par n'importe qui.

Conséquence à connaître : tant que le secret `NETLIFY_AUTH_TOKEN` est absent,
les agrégats sont publiés dans Git mais le site n'est pas redéployé. La tâche
émet alors un avertissement explicite plutôt que de sauter l'étape en silence.

---

## Surprises sur les données

**Le miroir et la source ne servent pas le même emballage.** L'ANS livre bien l'archive `Extraction_Correspondance_MSSante_AAAAMMJJhhmm.zip` décrite au brief, 20 Mo, contenant un unique fichier texte de 89 Mo ; data.gouv sert ce même texte décompressé, sans horodatage dans le nom. Identité vérifiée au 26/08/2026, taille interne et nombre de lignes identiques des deux côtés : le miroir est un report strict.

**Le fichier ne porte aucune date.** Ni création, ni modification, ni identifiant technique de BAL : l'adresse est la seule clé. L'historique par domaine ne peut donc pas être reconstitué, il doit être observé. C'est le constat qui a fermé l'option « rattraper le passé ».

**Le calendrier, lui, était déjà connu.** L'API `activity` de data.gouv conserve 294 événements de publication depuis octobre 2025 : publication **quotidienne, 7 j/7, week-ends et jours fériés compris**, 95,7 % des jours. La période d'apprentissage sans alerte prévue au brief est devenue sans objet pour la couche 0, et l'état météo « hors calendrier » restera inutilisé — aucun jour n'est normalement non publié.

**Il n'y a pas de BAL applicative dans cette source.** Deux types seulement, `PER` et `ORG`. La restitution n'affichera que deux catégories, et la page méthode devra dire pourquoi.

**La couche 0 ne coûte plus de téléchargement.** Le nom de fichier renvoyé dans les en-têtes de l'ANS porte l'horodatage de génération : la fraîcheur se vérifie sans transférer un octet de contenu, et le traitement complet ne se déclenche que si cet horodatage a bougé.

**L'annuaire vivait pendant que l'extraction était morte.** Du 30 juillet au 8 août 2026, aucune extraction déposée, mais `Organization?_lastUpdated` retourne 98 176 sur la même fenêtre. Le découpage du bulletin météo en maillons distincts est validé sur un cas réel avant d'avoir été construit.

**La contraction ne vient pas des domaines qui ferment.** Entre le 11 juin et le 25 août : 25 756 créations pour 36 119 suppressions, soit un solde de −10 363 masquant 61 875 mouvements. Sur ces 36 119 suppressions, **1 633 seulement s'expliquent par la disparition d'un domaine** : 95 % surviennent à l'intérieur de domaines toujours actifs, très majoritairement sur des BAL organisationnelles (−12 857). Le solde net est donc doublement trompeur, et le calcul séparé des créations et des suppressions prescrit au §8 du brief se vérifie sur données réelles.
