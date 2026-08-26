# 00 — Cartographie des sources

**État : validé le 26 août 2026.** Rapport d'étape 0. Les trois arbitrages qu'il appelait ont été rendus et sont consignés dans `docs/journal.md`.

Date des relevés : **26 août 2026**. Toutes les valeurs de ce document sont mesurées, aucune n'est reprise d'une documentation. Les commandes de vérification figurent en annexe pour que chaque chiffre soit rejouable.

---

## 1. Résumé pour décision

Cinq constats commandent l'architecture.

1. **Le fichier ne contient aucune date.** Ni création, ni modification, ni identifiant technique de BAL. L'historique par domaine ne peut pas être reconstitué : il doit être observé jour après jour. C'est le constat qui ferme l'option « rattraper le passé depuis les données ».
2. **La source quotidienne est le webservice d'extraction de l'ANS ; data.gouv.fr devient le second point d'observation.** Le webservice présente un certificat de racine IGC-Santé, absente des magasins publics : il faut lui fournir cette racine, publique, versionnée dans le dépôt. Une fois ce point réglé, il est supérieur au miroir sur tous les critères — il est en amont, il livre l'horodatage de génération réel, et il pèse 20 Mo au lieu de 89.
3. **La couche 0 ne coûte rien, et la diffusion devient mesurable.** Une requête d'en-têtes sur le webservice retourne le nom de fichier horodaté, sans transférer un octet de contenu. Comparé à l'horodatage de dépôt sur data.gouv, il donne en prime le **délai de diffusion** — la deuxième cellule du bulletin météo, que le brief prévoyait non instrumentée en v1.
4. **Le calendrier réel est déjà connu, rétroactivement.** L'API `activity` de data.gouv conserve 294 événements de publication depuis le 29 octobre 2025. La publication est **quotidienne, 7 j/7, week-ends et jours fériés compris**. La période d'apprentissage sans alerte prévue au brief peut être supprimée.
5. **Une interruption de dix jours est visible dans cet historique, du 30 juillet au 8 août 2026**, et l'annuaire continuait d'être alimenté pendant ce temps. Le dispositif à deux points d'observation est donc validé sur un cas réel, avant d'être construit.

---

## 2. Source principale : extraction des BAL MSSanté

### 2.1 Adresses

| | |
|---|---|
| Jeu de données | `annuaire-sante-extraction-des-bal-mssante` sur data.gouv.fr |
| Identifiant de jeu | `6902546dfc27585fa038d104` |
| Identifiant de ressource | `afe01105-d9a1-41fe-921f-e40ea48b2ba6` |
| Métadonnées (JSON, quelques Ko) | `https://www.data.gouv.fr/api/1/datasets/annuaire-sante-extraction-des-bal-mssante/` |
| Téléchargement stable | `https://www.data.gouv.fr/api/1/datasets/r/afe01105-d9a1-41fe-921f-e40ea48b2ba6` |
| Téléchargement horodaté | `https://static.data.gouv.fr/resources/annuaire-sante-extraction-des-bal-mssante/AAAAMMJJ-hhmmss/extraction-correspondance-mssante.txt` |
| Rôle | **second point d'observation** — voir §2.5 |
| Licence | Licence Ouverte v2 (`lov2`) |
| Fréquence déclarée | quotidienne — **conforme à l'observation**, voir §4 |
| Producteur | Agence du Numérique en Santé |

**Source primaire, en amont** : `https://service.annuaire.sante.fr/annuaire-sante-webservices/V300/services/extraction/Extraction_Correspondance_MSSante`. En libre accès, sans authentification. Voir §2.5.

### 2.2 Format

Les deux points d'entrée servent **le même contenu**, sous deux emballages :

- **ANS** : archive ZIP de **20 453 398 octets**, contenant un unique fichier `Extraction_Correspondance_MSSante_AAAAMMJJhhmm.txt` de **89 276 703 octets**. Le nom de fichier porte l'horodatage de génération. Conforme à ce qu'annonçait le brief.
- **data.gouv** : le même texte, **décompressé**, 89 276 703 octets, sans horodatage dans le nom.

Identité vérifiée au 26/08/2026 : taille interne au bit près et **535 928 lignes** des deux côtés. Le miroir est un report strict, pas une reconstruction.

Texte UTF-8, séparateur **`|`**, une ligne d'en-tête, **31 colonnes**, aucune ligne mal formée sur les trois fichiers examinés.

Colonnes, dans l'ordre :

```
Type de BAL | Adresse BAL | Type Identifiant PP | Identifiant PP |
Identification nationale PP | Type identifiant structure | Identification Structure |
Service de rattachement | Civilité d'exercice | Nom d'exercice | Prénom d'exercice |
Catégorie profession | Libellé de catégorie profession | Code Profession | Libellé Profession |
Code savoir-faire | Libellé savoir-faire | Dématérialisation |
Raison Sociale structure BAL | Enseigne commerciale structure BAL |
L2COMPLEMENTLOCALISATION | L3COMPLEMENTDISTRIBUTION | L4NUMEROVOIE |
L4COMPLEMENTNUMEROVOIE | NL4TYPEVOIE | L4LIBELLEVOIE | L5LIEUDITMENTION |
L6LIGNEACHEMINEMENT | Code postal | Département | Pays
```

Seules les colonnes **1 et 2** sont nécessaires à l'outil. Les 29 autres sont nominatives ou descriptives et n'ont aucun usage ici : elles ne doivent jamais sortir du traitement.

### 2.3 Ce que le fichier ne contient pas — point le plus structurant

- **Aucune date de création de la BAL.**
- **Aucune date de dernière modification de l'enregistrement.**
- **Aucun identifiant technique stable de BAL.** L'adresse elle-même est la seule clé.

Conséquences, à intégrer telles quelles dans l'architecture :

1. Les créations et suppressions ne s'obtiennent que par **différence d'ensembles entre deux observations successives**. Il faut donc persister l'état de la veille, sous forme d'empreintes salées, hors dépôt Git.
2. **L'historique antérieur au démarrage de l'outil est définitivement perdu** pour la vue par domaine. La série par domaine commencera à J+1 du premier cycle. À dire explicitement sur la page publique.
3. La clé de rapprochement étant l'adresse, un changement d'adresse se lira comme une suppression suivie d'une création. Limite à documenter au même titre que la liste rouge.

### 2.4 Types de BAL réellement présents

Deux valeurs seulement dans la colonne 1 : **`PER`** et **`ORG`**.

| Type | 11/06/2026 | 25/08/2026 |
|---|---:|---:|
| `PER` — personnelle | 456 654 | 455 471 |
| `ORG` — organisationnelle | 89 055 | 79 886 |
| **Total** | **545 709** | **535 357** |

**Il n'y a pas de BAL applicative dans cette source.** Le §3 du brief prévoyait une répartition en trois types ; la restitution n'en affichera que deux, et la page méthode devra dire pourquoi. À vérifier séparément : les BAL applicatives sont probablement portées par la ressource FHIR `Device`, qui ne compte que **191** occurrences — ordre de grandeur sans commune mesure, à ne pas présenter comme la population applicative réelle sans instruction complémentaire.

### 2.5 Répartition des rôles entre les deux points d'entrée

La chaîne TLS de `service.annuaire.sante.fr` est la suivante :

```
0 s: CN=service.annuaire.sante.fr, O=AGENCE DU NUMERIQUE EN SANTE   (exp. 04/05/2028)
1 s: CN=AC IGC-SANTE ELEMENTAIRE ORGANISATIONS, O=ASIP-SANTE        (exp. 24/06/2033)
2 s: CN=AC RACINE IGC-SANTE ELEMENTAIRE, O=ASIP-SANTE               (exp. 25/06/2033)
```

La racine est **IGC-Santé**, pas une autorité publique : sans ancre de confiance explicite, `curl` comme Python échouent en vérification de certificat, et un exécuteur GitHub échouerait de même. **Fournie en ancre, la connexion aboutit** : requête d'en-têtes en HTTP 200, téléchargement complet en 1,9 s.

Cette racine est un certificat **public**, valable jusqu'en **juin 2033**. Elle est versionnée dans le dépôt et passée explicitement au client, sans jamais modifier le magasin de confiance du système. Aucun secret, aucune dépendance à l'environnement d'exécution, et un tiers rejoue le pipeline à l'identique : l'argument de reproductibilité est préservé.

**Ce que la source ANS apporte et que le miroir ne peut pas donner.**

La réponse d'en-têtes contient :

```
Content-Disposition: attachment; filename=Extraction_Correspondance_MSSante_202608261013.zip
Content-Length: 20453398
```

- **L'horodatage de génération réel**, dans le nom de fichier, obtenu **sans transférer un octet de contenu**. Le champ `source_timestamp` du modèle de données retrouve donc le sens que lui donnait le brief : date et heure de génération par l'ANS. La réserve formulée en première rédaction de ce rapport tombe.
- **Un volume divisé par 4,4** : 20 Mo compressés contre 89 Mo en clair.
- **Aucune authentification.** L'extraction `Correspondance_MSSante` est en libre accès : la requête aboutit sans clé ni certificat client. Des droits d'accès étendus ne changent rien à ce fichier ; ils n'ouvriraient que des extractions en accès restreint, écartées au §6.2.

**Ce que le miroir data.gouv apporte encore, et pourquoi il reste au dispositif.**

1. **Un second point d'observation, gratuit, sur le maillon diffusion.** L'écart entre l'horodatage de génération ANS et l'horodatage de dépôt data.gouv mesure directement le délai de diffusion. Au 26/08/2026 : génération à 10:13, dépôt à 10:15:43 heure de Paris, soit **environ deux minutes trente**. Une source qui avance pendant que l'autre stagne localise la rupture sans ambiguïté — c'est exactement le raisonnement du §5.2 du brief, et il devient instrumentable en v1 au lieu d'être reporté en v2.
2. **Une empreinte et un nombre de lignes publiés**, utilisables en contrôle croisé de notre propre calcul.
3. **Une solution de repli** si le webservice devient indisponible, et **la mémoire du calendrier** via l'API `activity` (§4.2), que l'ANS n'expose nulle part.

**Décision : l'ANS est la source de contenu, data.gouv est le témoin de diffusion.** Aucune des deux n'est redondante.

## 3. Stratégie de collecte et de parsing

### 3.1 La sonde légère

**Cycle court, toutes les quatre heures — une requête d'en-têtes sur l'ANS.** Elle retourne le nom de fichier horodaté et la taille de l'archive, sans transférer de contenu. C'est la couche 0, prise à la source. Le traitement complet se déclenche si et seulement si l'horodatage a changé depuis la dernière observation.

**En complément, une requête de métadonnées sur data.gouv**, quelques kilo-octets :

| Champ | Valeur au 26/08/2026 | Usage |
|---|---|---|
| `url` (chemin horodaté) | `…/20260826-081543/…` | **délai de diffusion**, par écart avec l'horodatage ANS |
| `last_modified` | `2026-08-26T08:15:48+00:00` | idem |
| `extras['analysis:checksum']` (SHA-1) | `8d880d3c…d643c` | contrôle croisé de notre propre empreinte |
| `extras['analysis:content-length']` | `89 276 703` | contrôle de cohérence |
| profil tabulaire, `total_lines` | `535 928` | volumétrie de repli si le traitement lourd échoue |

Deux requêtes légères par cycle alimentent donc **deux des trois cellules du bulletin météo** : alimentation et publication d'un côté, diffusion de l'autre.

La couche 1 — republication à l'identique — se calcule désormais sur **notre propre empreinte SHA-256** du texte décompressé, obtenue au fil du parsing sans coût supplémentaire. C'est préférable à l'empreinte SHA-1 de data.gouv : elle porte sur la source primaire et ne dépend d'aucun traitement tiers. Le SHA-1 du miroir reste utile en contrôle croisé — une divergence signalerait une altération entre les deux points, ce qu'aucun autre indicateur ne verrait.

### 3.2 Parsing : lecture en flux du texte brut

L'archive contient un fichier unique : elle se lit **en flux, sans écriture sur disque**, via la bibliothèque standard `zipfile`.

Mesure sur le fichier du 25/08 (89 Mo décompressés), lecture ligne à ligne en Python, calcul simultané de l'empreinte SHA-256, du décompte par type, du décompte par domaine et des empreintes d'adresses :

- **0,64 s** de temps réel, **74 Mo** de mémoire résidente maximale, hors décompression.
- Téléchargement des 20 Mo : **1,9 s** mesurées.

Le critère d'acceptation n°4 est satisfait très largement. Un exécuteur GitHub sera plus lent d'un facteur 3 à 5, ce qui laisse le traitement complet sous la dizaine de secondes hors téléchargement. Aucune bibliothèque tierce n'est nécessaire : bibliothèque standard uniquement.

Un **Parquet de 19 Mo** est également généré par data.gouv (`extras['analysis:parsing:parquet_url']`) et permettrait de ne lire que deux colonnes. **Écarté** : il ajoute une dépendance `pyarrow`, il est produit par un composant interne de data.gouv sans engagement de service, et le ZIP de l'ANS pèse désormais à peine plus pour un contenu de source primaire. Sans objet une fois la source ANS retenue.

### 3.3 État de référence

535 188 adresses distinctes, soit autant d'empreintes tronquées à 8 octets : **4,3 Mo** sous forme compacte, très en deçà des 10 Go du cache GitHub Actions. Le dimensionnement prévu au brief tient sans réserve.

À noter : 535 357 lignes pour 535 188 adresses distinctes, soit **169 adresses apparaissant sur plusieurs lignes**. La déduplication sur l'adresse est donc obligatoire avant tout calcul de différence, faute de quoi le comptage serait faux de façon marginale mais permanente.

---

## 4. Historique et calendrier réel

### 4.1 Les versions antérieures ne sont pas conservées

Les URL horodatées sont **désactivées dès qu'une nouvelle version est déposée** : les quatre chemins antérieurs retrouvés en archive renvoient tous **404** aujourd'hui. data.gouv ne conserve que la version courante.

Seule exception, marginale mais réelle : **Internet Archive a capturé quatre versions complètes** (10/01, 17/02, 11/03 et 23/04/2026, environ 91 Mo chacune, corps intégral disponible). Cela permettrait de constituer quatre points d'ancrage rétrospectifs par domaine. Utile pour valider la méthode, insuffisant pour une série. À traiter comme un bonus de mise au point, pas comme une source.

### 4.2 Le calendrier de publication, lui, est reconstituable — et il est connu

L'API `activity` de data.gouv conserve l'historique des dépôts. **294 événements de mise à jour** relevés, du 29/10/2025 au 26/08/2026.

| | |
|---|---:|
| Période couverte | 302 jours |
| Jours avec publication | **289 (95,7 %)** |
| Jours sans publication | 13 |

Répartition par jour de semaine des jours publiés : lundi 42, mardi 42, mercredi 41, jeudi 40, vendredi 41, **samedi 41, dimanche 42**.

**La publication est quotidienne, sept jours sur sept, week-ends et jours fériés compris.** Le 15 août 2026 comme les dimanches sont publiés normalement. L'hypothèse d'un rythme ouvré est écartée par la mesure.

Conséquences directes :

- **La période d'observation sans alerte prévue au §8 du brief n'a plus lieu d'être** pour la couche 0. Le calendrier est établi ; l'alerte de fraîcheur nationale peut être armée dès la mise en service. Seules les couches 2 et 3, qui dépendent des différences par domaine, ont besoin d'accumuler des observations.
- L'**état neutre « hors calendrier »** de l'échelle météo devient inutile en pratique : il n'existe pas de jour normalement non publié. Le conserver dans le modèle, mais ne jamais l'employer par défaut.
- `docs/calendrier-observe.md` peut être produit **immédiatement**, à partir de cette source, plutôt qu'après plusieurs semaines.

Heure de dépôt, en UTC : 03 h dans 141 cas sur 294, 02 h dans 47 cas, le reste étalé jusqu'à 10 h, avec quelques dépôts tardifs en fin de journée. La cadence de sonde proposée au brief — 05:10, 09:10, 13:10, 17:10, 21:10 heure de Paris — couvre correctement cette dispersion. Le premier passage de la journée doit toutefois être considéré comme normalement porteur du fichier du jour, et un fichier absent à 09:10 Paris est déjà une anomalie de premier niveau.

### 4.3 Les trois interruptions observées

| Période | Durée | Jours |
|---|---:|---|
| 29–30 avril 2026 | 2 j | mer.–jeu. |
| 6 mai 2026 | 1 j | mer. |
| **30 juillet – 8 août 2026** | **10 j** | jeu.–sam. |

La troisième est l'incident de référence décrit au §1 du brief. **Il a eu lieu à l'été 2026 : l'année portée au brief était une erreur, corrigée le 26/08/2026.** Le cas de référence a donc trois semaines, et non treize mois — le jeu de données de test du critère d'acceptation n°1 peut être bâti sur des données réelles et récentes plutôt que reconstitué.

Réserve de méthode : ces événements attestent d'une absence de dépôt **sur data.gouv**. Ils ne distinguent pas à eux seuls une non-production par l'ANS d'une non-reprise par la plateforme. Le §5 lève cette ambiguïté pour l'épisode de juillet-août.

---

## 5. Deuxième point d'observation : l'API FHIR

Testée sur `https://gateway.api.esante.gouv.fr/fhir/v2`, en accès libre, avec une clé « données publiques » obtenue en self-service.

### 5.1 Ce qui fonctionne

- **`_total=accurate` fonctionne sur toutes les ressources testées.** Un décompte exact coûte une requête et un seul enregistrement transféré (`_count=1`). Relevés au 26/08/2026 : `PractitionerRole` 2 005 375, `Practitioner` 1 953 750, `Organization` 1 993 189, `Device` 191.
- **`_lastUpdated` est pris en charge, y compris en encadrement de deux bornes.** C'est le résultat le plus utile de ce rapport après le calendrier.

| Requête | Total |
|---|---:|
| `PractitionerRole?_lastUpdated=ge2026-08-25&_lastUpdated=lt2026-08-26` | 12 370 |
| `PractitionerRole?_lastUpdated=gt2026-08-20` | 20 332 |
| `Organization?_lastUpdated=gt2026-08-20` | 3 814 |

L'annuaire expose donc un **indicateur d'activité quotidien, national, indépendant de la chaîne d'extraction, pour deux requêtes par cycle**. C'est exactement le trancheur cherché au §5.2 du brief : si l'extraction est figée et que `_lastUpdated` progresse, la rupture est en aval de l'ingestion.

**Vérification sur l'épisode réel.** Sur la fenêtre du 30 juillet au 8 août 2026, pendant laquelle aucune extraction n'a été déposée, `Organization?_lastUpdated=ge2026-07-30&_lastUpdated=lt2026-08-09` retourne **98 176**. L'annuaire était alimenté pendant que l'extraction ne l'était plus. Le découpage en maillons distincts du bulletin météo n'est donc pas une précaution théorique : il aurait produit un diagnostic juste, au bon endroit, dès le deuxième jour.

### 5.2 Ce qui ne fonctionne pas

- **`_summary=count` n'existe pas** sur cette passerelle : elle répond `Parameter _summary not found`. Utiliser `_total=accurate`.
- **Il n'y a pas de décompte par domaine de messagerie.** Le paramètre `mailbox-mss` répond en égalité stricte sur une adresse complète. Avec le modificateur `:contains`, les résultats sont incohérents : `mssante.fr` retourne 50 735 `PractitionerRole`, alors que `medecin.mssante.fr` — plus de 62 000 BAL dans l'extraction — en retourne **0**. Le paramètre ne se comporte pas comme une chaîne indexée en sous-chaîne. **Réponse à la question du brief : non, l'API FHIR ne permet pas d'obtenir un décompte par domaine sans parcourir l'intégralité des ressources.** La vue par domaine repose donc entièrement sur l'extraction.

### 5.3 Deux réserves avant de bâtir dessus

1. `_lastUpdated` marque une **écriture technique**, pas nécessairement un changement métier. Une réindexation de masse le ferait progresser sans qu'aucune BAL ait bougé. L'indicateur est robuste pour détecter un **arrêt** — un zéro est un zéro — et fragile pour interpréter une **variation**. À restituer comme signal de vie, jamais comme volume de créations.
2. L'appel exige une **clé**, gratuite mais nominative. Elle ira dans les secrets du dépôt, ce qui est compatible avec le §6.4, mais **un tiers qui rejoue le pipeline devra obtenir la sienne**. La reproductibilité intégrale reste acquise sur la source principale, qui n'exige aucune authentification ; à mentionner dans la page méthode.

---

## 6. Ce que les données disent des questions restées ouvertes

Deux des quatre points en suspens du brief se tranchent sur mesure.

### 6.1 Regroupement des domaines de faible volume — question n°2

Distribution au 25/08/2026, sur **5 018 domaines** et 535 357 BAL :

| | |
|---|---:|
| Médiane | **4 BAL** |
| 90ᵉ centile | 87 |
| 99ᵉ centile | 1 193 |
| Maximum | 62 151 |
| Domaines sous 10 BAL | **3 234 (64 %)** |

Le seuil de 30 BAL évoqué au brief se vérifie remarquablement bien : **1 001 domaines atteignent 30 BAL ou plus et concentrent 95,8 % du volume**. Les 4 017 domaines restants pèsent **4,2 %** du total. Les regrouper dans un agrégat « autres » retire les deux tiers du bruit de la matrice sans rien retrancher de significatif, et évite d'exposer plusieurs milliers de très petits exploitants à une lecture erronée. **Acté le 26/08/2026 : regroupement au seuil de 30 BAL publiées**, seuil documenté dans la page méthode. Question n°2 du brief close.

Concentration, pour mémoire : les dix premiers domaines représentent 46 % du volume, les cinquante premiers 66 %.

### 6.2 Accès restreint — question n°3

Sans objet en pratique. La source retenue est en licence ouverte et sans authentification ; la seule composante nécessitant une clé est le point de contrôle FHIR, en tier public gratuit. **Recommandation : rester strictement sur les données en libre accès**, ce qui préserve l'argument de reproductibilité.

### 6.3 Un mouvement de fond que l'outil devra savoir ne pas confondre avec une panne

Différence d'ensembles entre les deux extractions disponibles, sur **75 jours** :

| | |
|---|---:|
| Créations | **25 756** |
| Suppressions | **36 119** |
| Solde | **−10 363** |

Dont, pour les seules BAL organisationnelles : 3 690 créations contre **12 857 suppressions**. Le nombre de domaines distincts passe de 5 316 à 5 018, avec 482 domaines disparus et 184 apparus.

Trois enseignements pour la conception :

1. **Le solde net est trompeur** : −10 363 en apparence, alors que 61 875 mouvements ont eu lieu. Le calcul séparé des créations et des suppressions, prescrit au §8 du brief, est indispensable et se vérifie ici sur données réelles.
2. Le rythme moyen est de l'ordre de **340 créations par jour** au niveau national, ce qui donne une échelle réaliste à l'histogramme et aux seuils.
3. La contraction porte massivement sur les BAL organisationnelles et sur des domaines entiers qui disparaissent. **L'outil affichera régulièrement des lignes qui blanchissent sans qu'aucun incident n'ait eu lieu.** La note « Lecture : » sous la matrice n'est pas une précaution rédactionnelle, c'est une nécessité de fond. La règle qui sépare un retrait de domaine d'une interruption de publication a été actée le 26/08/2026 : voir `docs/journal.md`, décision 4.

Attention enfin : ces 75 jours incluent l'interruption du 30 juillet au 8 août. Ces chiffres décrivent un écart entre deux photographies, pas un rythme régulier.

---

## 7. Ce qui change dans le brief

| § du brief | Élément | Correction |
|---|---|---|
| 5.1 | Archive ZIP | **Confirmé** côté ANS : ZIP de 20 Mo, un fichier texte de 89 Mo à l'intérieur. data.gouv sert le même texte décompressé |
| 5.1 | Source = webservice ANS | **Confirmé.** Exige de fournir la racine IGC-Santé, publique et versionnée dans le dépôt. data.gouv passe en témoin de diffusion |
| 9.2 | Cellule « diffusion » non instrumentée en v1 | **Instrumentable en v1** par l'écart entre horodatage ANS et dépôt data.gouv |
| 3 | Trois types de BAL | Deux seulement : `PER` et `ORG` ; pas d'applicative dans la source |
| 6.1 | Couche 0 après téléchargement | Couche 0 sur en-têtes seuls : le nom de fichier porte l'horodatage de génération |
| 7 | `source_timestamp` = génération ANS | **Conforme au brief** : le nom de fichier ANS porte la date et l'heure de génération |
| 8 | Apprentissage du calendrier sur plusieurs semaines | Calendrier déjà établi rétroactivement : quotidien 7 j/7 |
| 9.2 | État neutre hors calendrier | Conservé au modèle, mais inutilisé : aucun jour n'est normalement non publié |
| 5.2 | FHIR pour le décompte par domaine | Impossible ; FHIR sert de signal de vie national via `_lastUpdated` |
| 15-2 | Seuil de regroupement à évaluer | **Acté à 30 BAL** : 1 001 domaines (95,8 % du volume) contre 4 017 en agrégat « autres » |
| 8 | Créations nulles = signal | Un domaine en retrait sort du calcul d'anomalie : voir `docs/journal.md`, décision 4 |
| 1 | Incident de référence en 2025 | **Été 2026** — erreur de millésime au brief, corrigée |

---

## 8. Ce qui reste à vérifier avant de coder

1. **La désactivation des tâches planifiées après 60 jours** sur un dépôt public : à confirmer en service réel, avec l'alerte de non-production à 48 h comme filet, telle que prévue au §6.4.
2. **La stabilité de l'horodatage porté par le nom de fichier ANS** : vérifier sur une dizaine de cycles qu'il avance à chaque génération et ne reste pas figé. Toute la couche 0 en dépend.
3. **Le comportement de l'API `activity`** au-delà de la pagination observée : elle est ici notre unique mémoire du calendrier, et rien ne garantit qu'elle ne soit pas purgée.
4. **Les BAL applicatives** : déterminer si elles sont hors périmètre de l'extraction ou absentes de l'espace de confiance, avant d'écrire la page méthode.

---

## Annexe — commandes de vérification

```bash
# Métadonnées, empreinte, taille, horodatage de publication
curl -s "https://www.data.gouv.fr/api/1/datasets/annuaire-sante-extraction-des-bal-mssante/"

# Nombre de lignes, colonnes, séparateur — sans téléchargement
curl -s "https://tabular-api.data.gouv.fr/api/resources/afe01105-d9a1-41fe-921f-e40ea48b2ba6/profile/"

# Historique des publications (paginer sur next_page)
curl -s "https://www.data.gouv.fr/api/1/activity/?related_to=6902546dfc27585fa038d104&page_size=100"

# Chaîne TLS du webservice ANS
echo | openssl s_client -connect service.annuaire.sante.fr:443 \
  -servername service.annuaire.sante.fr 2>/dev/null | grep "^ [0-9] s:"

# Signal de vie de l'annuaire (clé publique requise)
curl -s -H "ESANTE-API-KEY: $ANS_API_KEY" \
  "https://gateway.api.esante.gouv.fr/fhir/v2/PractitionerRole?_lastUpdated=ge2026-08-25&_lastUpdated=lt2026-08-26&_count=1&_total=accurate"
```

Les décomptes par type, par domaine et les différences d'ensembles ont été calculés en local sur deux extractions du 11/06/2026 et du 25/08/2026, en lecture ligne à ligne. **Ces fichiers contiennent des données à caractère personnel et ne doivent jamais entrer dans le dépôt.** Le `.gitignore` doit exclure `*.txt` à la racine et tout fichier dépassant le plafond de taille défini au §11 du brief, avant le premier commit.
