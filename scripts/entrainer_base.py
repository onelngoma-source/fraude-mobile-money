"""Modèle de base : régression logistique, validation croisée temporelle."""

from pathlib import Path

import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from validation import plis_temporels
from variables import VARIABLES

df = pl.read_parquet("data/processed/variables_dev.parquet").sort("step", maintain_order=True)
X = df.select(VARIABLES).to_numpy().astype(float)
y = df["isFraud"].to_numpy()
steps = df["step"].to_numpy()

resultats = []
for pli, (i_ent, i_val) in enumerate(plis_temporels(steps), start=1):
    modele = make_pipeline(
        StandardScaler(),  # appris sur l'entraînement du pli seulement (D13)
        LogisticRegression(class_weight="balanced", max_iter=1000),
    )
    modele.fit(X[i_ent], y[i_ent])
    proba = modele.predict_proba(X[i_val])[:, 1]
    taux = y[i_val].mean()
    resultats.append({
        "pli": pli,
        "steps_validation": f"{steps[i_val][0]}-{steps[i_val][-1]}",
        "fraudes_validation": int(y[i_val].sum()),
        "taux_fraude_pct": round(100 * taux, 3),
        "pr_auc_hasard": round(taux, 4),
        "pr_auc": round(average_precision_score(y[i_val], proba), 4),
    })
    print(f"Pli {pli} terminé")

tableau = pl.DataFrame(resultats)
print(tableau)
print(f"PR-AUC moyenne : {tableau['pr_auc'].mean():.4f} (écart-type {tableau['pr_auc'].std():.4f})")

Path("reports").mkdir(exist_ok=True)
tableau.write_csv("reports/base_logistique_cv.csv")
