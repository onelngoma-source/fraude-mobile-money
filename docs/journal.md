# Journal de bord : détection de fraude mobile money

Ce journal consigne le cadrage, chaque décision prise avec sa justification, et chaque constat sur les données.

## 1. Cadrage du problème

**Question métier.** Un opérateur de mobile money veut repérer les transactions frauduleuses pour limiter ses pertes et protéger ses clients.

**Ce qui est prédit.** Pour une transaction, au moment où elle est demandée, la probabilité qu'elle soit frauduleuse.

**Information autorisée.** Uniquement ce qui est connu au moment de la demande. Toute colonne décrivant ce qui se passe après la transaction est exclue. Chaque colonne sera examinée avec cette règle.

**Décision.** Laisser passer, bloquer ou envoyer en vérification.

**Coûts des erreurs.**
- Fraude non détectée : perte du montant et perte de confiance du client victime.
- Client honnête bloqué : mécontentement, coût du service client, risque de départ vers un concurrent.

Les clients honnêtes étant beaucoup plus nombreux que les fraudeurs, le coût total des blocages à tort peut dépasser celui des fraudes évitées. Le seuil de décision sera donc fixé par un calcul de coût, avec une analyse de sensibilité aux hypothèses.

**Mesure du succès.** Rappel, précision, aire sous la courbe précision-rappel et coût total des erreurs. L'exactitude n'est pas utilisée : avec environ 0,13 % de fraudes, un modèle qui ne détecte rien aurait 99,87 % d'exactitude.

## 2. Règles de rigueur du projet

1. Le jeu de test est mis de côté avant toute exploration approfondie et utilisé une seule fois, à la fin.
2. Les découpages respectent l'ordre du temps : jamais d'entraînement sur des transactions postérieures à celles évaluées.
3. Les hyperparamètres sont choisis uniquement par validation croisée temporelle sur les données d'entraînement.
4. La calibration des probabilités est vérifiée avant de fixer un seuil.
5. Chaque colonne est contrôlée pour les fuites d'information.
6. Les résultats sont reproductibles : versions figées, graines aléatoires fixées, étapes scriptées.
7. Les limites sont documentées.

## Provenance des données

| Élément | Valeur |
|---|---|
| Source | Kaggle, jeu `ealaxi/paysim1` : https://www.kaggle.com/datasets/ealaxi/paysim1 |
| Licence | CC BY-SA 4.0 (citation obligatoire, données dérivées sous la même licence) |
| Fichier | `PS_20174392719_1491204439457_log.csv` |
| Taille | 471 Mo (archive téléchargée : 178 Mo) |
| Lignes | 6 362 621, soit 6 362 620 transactions et une ligne d'en-tête |
| Colonnes | 11 : step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud |
| Empreinte SHA-256 | `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b` |
| Date de téléchargement | 2026-11-05 |

Pour vérifier qu'un fichier téléchargé est identique : `sha256sum data/raw/*.csv` doit renvoyer la même empreinte.

## Dictionnaire des données

Une ligne correspond à une transaction. Période simulée : 744 heures (31 jours). Données synthétiques générées par le simulateur PaySim à partir des journaux réels d'un service de mobile money africain.

| Colonne | Signification | Remarques |
|---|---|---|
| step | Heure de la simulation (1 à 744) | Pas une vraie date ; l'heure de départ n'est pas connue |
| type | CASH_IN, CASH_OUT, DEBIT, PAYMENT ou TRANSFER | |
| amount | Montant de la transaction | Monnaie non précisée : unités monétaires |
| nameOrig | Identifiant de l'expéditeur (C = client) | Anonyme |
| oldbalanceOrg | Solde de l'expéditeur avant la transaction | Orthographe « Org » d'origine, conservée |
| newbalanceOrig | Solde de l'expéditeur après la transaction | Décrit la situation après l'opération |
| nameDest | Identifiant du destinataire (C = client, M = marchand) | |
| oldbalanceDest | Solde du destinataire avant | Non renseigné pour les marchands |
| newbalanceDest | Solde du destinataire après | Incohérences observées (H3) |
| isFraud | Cible : 1 = fraude, 0 = normale | |
| isFlaggedFraud | Signalement par une règle existante (virements de plus de 200 000) | Règle métier, pas la vérité terrain |

Point à vérifier dans la description officielle : avertissement des auteurs sur l'usage des colonnes de soldes pour la détection de fraude.

## 3. Décisions

| N° | Date | Décision | Justification |
|---|---|---|---|
| D1 | 2026-11-05 | L'exactitude n'est pas une métrique du projet | Dominée par la classe majoritaire (99,87 % sans rien détecter) |
| D2 | 2026-11-05 | Python 3.12 | Version stable compatible avec LightGBM, SHAP et MLflow |
| D3 | 2026-11-05 | Les données brutes ne sont jamais modifiées | Pouvoir toujours revenir à la source |
| D4 | 2026-11-05 | DuckDB, Polars et Parquet pour manipuler les données | Rapides et économes en mémoire sur plus de 6 millions de lignes, sans serveur |
| D5 | 2026-11-05 | Source des données : `ealaxi/paysim1` sur Kaggle (version d'avril 2017) | Publication originale de l'auteur du simulateur, la plus utilisée et la plus citée ; les nombreuses copies peuvent être modifiées ou de provenance inconnue |

## 4. Constats sur les données

### Hypothèses issues de l'observation (à vérifier sur l'ensemble des données)

| N° | Hypothèse | Observée sur | Statut |
|---|---|---|---|
| H1 | Les fraudes n'apparaissent que dans les types TRANSFER et CASH_OUT | Premières lignes et échantillon de 500 fraudes | À vérifier |
| H2 | Une fraude vide entièrement le compte de l'expéditeur (montant égal au solde avant, solde après à 0) | Lignes 3 et 4 du fichier | À vérifier |
| H3 | Les soldes du destinataire sont souvent incohérents avec le montant reçu (solde après à 0 malgré l'argent reçu) | Lignes 3 et 4 du fichier | À vérifier |