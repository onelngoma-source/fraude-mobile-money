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

## 3. Décisions

| N° | Date | Décision | Justification |
|---|---|---|---|
| D1 | 2026-11-05 | L'exactitude n'est pas une métrique du projet | Dominée par la classe majoritaire (99,87 % sans rien détecter) |
| D2 | 2026-11-05 | Python 3.12 | Version stable compatible avec LightGBM, SHAP et MLflow |
| D3 | 2026-11-05 | Les données brutes ne sont jamais modifiées | Pouvoir toujours revenir à la source |

## 4. Constats sur les données

*À compléter à partir de l'étape suivante.*