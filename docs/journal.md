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
| Échantillonnage | Le fichier contient environ un quart de la simulation originale (selon la description officielle) |

| Période | 744 steps d'une heure, soit 31 jours (la description indique 30 jours : incohérence à noter) |

| Méthode d'échantillonnage | Non documentée : on ne sait pas si le quart publié a été tiré par transaction ou par client. Conséquence possible : historiques de comptes incomplets (à mesurer) |

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

Avertissement vérifié dans la description officielle : les transactions détectées comme fraudes sont annulées, les quatre colonnes de soldes ne doivent pas être utilisées pour la détection (voir D6).

## 3. Décisions

| N° | Date | Décision | Justification |
|---|---|---|---|
| D1 | 2026-11-05 | L'exactitude n'est pas une métrique du projet | Dominée par la classe majoritaire (99,87 % sans rien détecter) |
| D2 | 2026-11-05 | Python 3.12 | Version stable compatible avec LightGBM, SHAP et MLflow |
| D3 | 2026-11-05 | Les données brutes ne sont jamais modifiées | Pouvoir toujours revenir à la source |
| D4 | 2026-11-05 | DuckDB, Polars et Parquet pour manipuler les données | Rapides et économes en mémoire sur plus de 6 millions de lignes, sans serveur |
| D5 | 2026-11-05 | Source des données : `ealaxi/paysim1` sur Kaggle (version d'avril 2017) | Publication originale de l'auteur du simulateur, la plus utilisée et la plus citée ; les nombreuses copies peuvent être modifiées ou de provenance inconnue |
| D6 | 2026-11-05 | Les colonnes oldbalanceOrg, newbalanceOrig, oldbalanceDest et newbalanceDest ne sont jamais utilisées comme variables du modèle | Avertissement explicite des auteurs : les fraudes détectées sont annulées, ces soldes reflètent donc le traitement de la fraude (fuite de données). Conservées uniquement pour l'exploration |
| D7 | 2026-11-05 | Les analyses utilisent data/interim/paysim.parquet, produit par scripts/convertir_parquet.py | Copie exacte du CSV prouvée (totaux de contrôle et comparaison ligne par ligne), lecture beaucoup plus rapide |
| D8 | 2026-11-06 | Les hypothèses sur la fraude (H1, H2, H3, H7) sont vérifiées uniquement sur les données d'entraînement, après la mise de côté du jeu de test | Toute observation faite sur le jeu de test influencerait nos choix et rendrait l'évaluation finale trop optimiste |
| D9 | 2026-11-06 | Découpage temporel : jeu de développement = premiers steps jusqu'au step où le cumul atteint 80 % des transactions (coupure entre deux steps) ; jeu de test = steps suivants jusqu'au step 743 | Respect de l'ordre du temps ; le test couvre la fin de la période chargée et toute la période calme. Option « 7 derniers jours » écartée : trop peu de fraudes probables et une seule période représentée |
| D9 (précision) | 2026-11-06 | Step de coupure = 355 (jour 15, 18 h). Développement : steps 1 à 355, 5 113 884 transactions (80,37 %). Test : steps 356 à 743, 1 248 736 transactions (19,63 %) | Application de la règle D9 sans ajustement après avoir vu le résultat |
| D10 | 2026-11-06 | Les hyperparamètres sont choisis par validation croisée temporelle à l'intérieur du jeu de développement | Le jeu de test reste intact jusqu'à l'évaluation finale |
| D11 | 2026-11-06 | Les résultats finaux sont présentés globalement et séparément pour la période chargée et la période calme | Le modèle est entraîné presque uniquement sur la période chargée ; un score global masquerait l'écart entre les deux |
| D12 | 2026-11-06 | Jeu de test scellé : data/processed/test.parquet, lecture seule, jamais régénéré. Empreinte sha256 : 220c6c02cbf6ca807a43a95ac443e99a1aa4bdeef60b03408d3553624b344e36 | Prouver à la fin du projet que l'évaluation porte sur le fichier d'origine, intact |
| D13 | 2026-11-06 | Toute opération qui apprend des données (normalisation, remplissage, seuils) est calculée sur la partie entraînement de chaque découpage, via un pipeline scikit-learn | Éviter les fuites de données, y compris pendant la validation croisée |
| D14 | 2026-11-06 | Le modèle ne traite que les TRANSFER et CASH_OUT. L'évaluation finale porte sur tout le jeu de test : les transactions des autres types sont comptées comme non signalées | Sur le développement, ces deux types contiennent 100 % des fraudes pour 44 % des transactions (une fraude pour 565 au lieu de 1 290). Évaluer sur tout le test évite de masquer d'éventuelles fraudes hors périmètre |
| Limite | 2026-11-06 | Des fraudeurs réels pourraient se reporter sur PAYMENT, CASH_IN ou DEBIT | En production, prévoir une surveillance des autres types et un élargissement du périmètre si des fraudes y apparaissent |

## 4. Constats sur les données


### Constat : cycle quotidien
En supposant que le step 1 correspond à minuit (déduction, non documentée) : creux entre 1 h et 6 h (minimum 1 241 transactions à 3 h), activité forte de 8 h à 19 h, pic à 18 h (647 814). L'heure est une variable candidate, connue au moment de la transaction.

### Chiffres de référence (mesurés le 2026-11-05 lors de la conversion en Parquet)

| Mesure | Valeur |
|---|---|
| Transactions | 6 362 620 |
| Fraudes (isFraud = 1) | 8 213, soit 0,129 % (environ 1 sur 775) |
| Signalements de l'ancienne règle (isFlaggedFraud = 1) | 16, soit au mieux 0,19 % des fraudes détectées |
| Steps | De 1 à 743 (la documentation annonce 744) |
| Types de transactions | 5 |
| Valeurs vides (NULL) | 0 |
| Somme des montants | 1 144 392 944 759,77 unités monétaires |
| Taille | 494 Mo en CSV, 262 Mo en Parquet |
### Répartition des transactions dans le temps (notebook 01, sans utiliser isFraud)

- Volume horaire très irrégulier : moyenne 8 563, médiane 529, minimum 2, maximum 51 352.
- Quatre périodes : jours 1-2 (16,2 % des transactions), jours 3-5 (0,6 %), jours 6-17 (77,3 %), jours 18-31 (5,9 %, volume environ 20 fois plus faible).
- Le jour 31 est incomplet (272 transactions, arrêt au step 743).
- Rythme quotidien probable (environ un pic par 24 steps) : à confirmer par la répartition par heure du jour.
- Conséquence : la fin de la période ne ressemble pas au reste (changement de distribution), à prendre en compte pour le découpage entraînement/test.

## Découpage effectué (scripts/decouper_dev_test.py)
Développement : 5 113 884 transactions (80,37 %), steps 1 à 355.
Test : 1 248 736 transactions (19,63 %), steps 356 à 743.
6 contrôles OK : lignes, steps, somme des montants, comparaison ligne par ligne dans les deux sens. Aucun contrôle ne lit isFraud dans le test.

### Hypothèses issues de l'observation (à vérifier sur l'ensemble des données)

| N° | Hypothèse | Observée sur | Statut |
|---|---|---|---|
| H1 | Les fraudes n'apparaissent que dans les types TRANSFER et CASH_OUT | Premières lignes et échantillon de 500 fraudes | À vérifier |
| H2 | Une fraude vide entièrement le compte de l'expéditeur (montant égal au solde avant, solde après à 0) | Lignes 3 et 4 du fichier | À vérifier |
| H3 | Les soldes du destinataire sont souvent incohérents avec le montant reçu (solde après à 0 malgré l'argent reçu) | Lignes 3 et 4 du fichier | À vérifier |
| H4 | Les historiques des comptes sont incomplets ou très courts (chaque identifiant apparaît peu de fois) | Description officielle (un quart de la simulation) | À vérifier |
| H5 | Des valeurs manquantes sont déguisées en zéros (soldes des marchands non renseignés) | Documentation et contrôle (0 NULL malgré des soldes non renseignés) | À vérifier |
| H6 | Tous les steps de 1 à 743 ne sont peut-être pas présents | Dernier step à 743 au lieu de 744 | **Réfutée** : les 743 steps sont présents (notebook 01) |
| H7 | Les 16 signalements de l'ancienne règle sont tous des fraudes | Contrôle de conversion | À vérifier |
| H8 | Les fraudes ont une répartition horaire différente des transactions normales | À vérifier sur le jeu de développement uniquement |

| H1 | ... | Confirmée sur le développement : 100 % des 3 963 fraudes sont en TRANSFER (1 972) ou CASH_OUT (1 991). 0 fraude parmi les 2 875 415 PAYMENT, CASH_IN et DEBIT. Propriété du simulateur, pas forcément de la réalité |
| H9 | 2026-11-06 | Chaque fraude est une paire : un TRANSFER vers un compte du fraudeur, puis un CASH_OUT du même montant | À vérifier sur le jeu de développement |

### Constat : taux de fraude différent entre développement et test
Développement : 3 963 fraudes sur 5 113 884 (0,077 %). Test : 4 250 fraudes sur 1 248 736 (0,34 %), déduit par soustraction du total de 8 213 établi avant le découpage. Aucune autre information du test n'a été consultée. Conséquences : la précision sera mécaniquement plus élevée sur le test, et les probabilités du modèle risquent d'être sous-estimées. À prendre en compte pour la calibration et l'interprétation des résultats.



| H2 | ... | Confirmée : 98,13 % des fraudes vident le compte, 0 % des transactions normales. Repose sur les soldes, donc inutilisable (D6) |
| H5 | ... | Confirmée : 47,73 % des transactions normales partent d'un solde nul, les zéros signifient souvent « inconnu » |
| H9 | ... | Confirmée : 1 993 paires TRANSFER puis CASH_OUT pour 1 972 transferts frauduleux. Inutilisable comme variable (le retrait est postérieur) |
| Constat | 2026-11-21 | Montant maximal des fraudes = 10 000 000 exactement : plafond du simulateur. Variable montant_10m conservée, signalée comme artefact |
| D15 | 2026-11-21 | Variables : type, heure, montant, historique des comptes émetteur et destinataire calculé jusqu'au step précédent | Uniquement des informations connues au moment de la transaction |
| D16 | 2026-11-21 | Validation croisée : 6 blocs consécutifs, 5 plis, entraînement sur le passé et validation sur le bloc suivant ; métrique principale PR-AUC | Respect de l'ordre du temps |

| Résultat | 2026-11-21 | Régression logistique (référence) : PR-AUC moyenne 0,105, écart-type 0,081. Plis 1 à 3 : 0,145 à 0,190 ; plis 4 et 5 : environ 0,02. Toujours au-dessus du hasard (× 11 à × 119) | Chute probable due aux compteurs cumulés depuis le début des données, dont l'échelle dérive avec le temps |
| D17 | 2026-11-21 | LightGBM réglé par Optuna (25 essais, échantillonneur TPE, graine 42) sur la PR-AUC moyenne des 5 plis ; nombre d'arbres réglé comme hyperparamètre, sans arrêt anticipé ; essais suivis dans MLflow | Corrige l'absence d'optimisation et de validation croisée du mémoire, sans réutiliser le pli de validation pour arrêter l'entraînement |

| Résultat | 2026-11-21 | LightGBM réglé : PR-AUC moyenne 0,406 (écart-type 0,029), plis de 0,357 à 0,446, contre 0,105 (0,081) pour la régression logistique | Plateau autour de 0,40 sur les essais 12 à 25 |
| Limite | 2026-11-21 | Meilleur n_estimators (100) à la borne basse, num_leaves (17) proche de la borne (15) | Gain attendu faible vu le plateau ; intervalle à élargir dans une version future |

| Résultat | 2026-11-21 | Régression logistique (référence) : PR-AUC moyenne 0,105, écart-type 0,081. Plis 1 à 3 : 0,145 à 0,190 ; plis 4 et 5 : environ 0,02. Toujours au-dessus du hasard (× 11 à × 119) | Chute probable due aux compteurs cumulés depuis le début des données, dont l'échelle dérive avec le temps |

| D17 | 2026-11-21 | LightGBM réglé par Optuna (25 essais, échantillonneur TPE, graine 42) sur la PR-AUC moyenne des 5 plis ; nombre d'arbres réglé comme hyperparamètre, sans arrêt anticipé ; essais suivis dans MLflow | Corrige l'absence d'optimisation et de validation croisée du mémoire, sans réutiliser le pli de validation pour arrêter l'entraînement |

| D18 | 2026-11-21 | Calibration isotonique apprise sur les prédictions hors pli. Règle : alerter si probabilité calibrée × montant ≥ coût d'une vérification (5 000), sensibilité testée à 1 000, 20 000 et 50 000 | Minimise le coût attendu ; n'a de sens qu'avec des probabilités calibrées |

| Résultat | 2026-11-21 | Calibration (pli 5) : probabilité moyenne 0,335 % brute, 0,199 % calibrée, pour 0,137 % réel ; Brier 0,001121 → 0,000978. PR-AUC 0,414 → 0,384 (paliers isotoniques) | Score brut pour le classement, probabilité calibrée pour la décision |
| Résultat | 2026-11-21 | Règle à 5 000 (pli 5) : 9 091 alertes, 67 % des fraudes et 96 % du montant fraudé détectés, coût 72,8 M contre 690,9 M sans modèle (−89 %). Réduction encore de 70 % à 50 000 | Conclusion robuste au choix du coût |
| Constat | 2026-11-21 | Variable la plus importante : heure (fraudes uniformes sur 24 h dans le simulateur). orig_nb_avant inutile (comptes émetteurs quasi uniques, H4 confirmée) | Artefacts de la simulation, à signaler dans le README |

| Résultat final | 2026-11-21 | Test (évalué une seule fois, empreinte vérifiée) : PR-AUC 0,539 (hasard 0,003), rappel 69 %, 97 % du montant fraudé détecté, précision 19 %, coût −96 % (6 683 M → 272 M). Période chargée : PR-AUC 0,497, rappel 67 %, précision 5 %. Période calme : PR-AUC 0,576, rappel 70 %, précision 33 %. Sensibilité : −87 % à −98 % selon le coût d'une vérification | Rappel et part du montant détecté stables par rapport à la validation croisée |
| Constat | 2026-11-21 | Calibration bonne en période chargée (0,185 % annoncé, 0,166 % réel), sous-estimation d'environ 2 fois en période calme (1,27 % contre 2,34 %) | Changement du taux de fraude, annoncé avant l'ouverture du test |
| Constat | 2026-11-21 | 0 fraude hors périmètre dans le test | Le choix D14 n'a rien coûté sur cette période |