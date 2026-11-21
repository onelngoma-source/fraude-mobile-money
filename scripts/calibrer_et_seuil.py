"""Calibration des probabilités et règle de décision selon les coûts (jeu de développement uniquement)."""

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss

from validation import plis_temporels
from variables import VARIABLES

COUT_VERIFICATION = 5_000  # coût d'une alerte (vérification par un agent)
SENSIBILITE = [1_000, 5_000, 20_000, 50_000]

params = json.loads(Path("reports/meilleurs_parametres_lightgbm.json").read_text())
df = pl.read_parquet("data/processed/variables_dev.parquet").sort("step", maintain_order=True)
X = df.select(VARIABLES).to_numpy().astype(np.float32)
y = df["isFraud"].to_numpy()
steps = df["step"].to_numpy()
montant = np.expm1(df["log_montant"].to_numpy())


def nouveau_modele():
    return lgb.LGBMClassifier(**params, objective="binary", random_state=42, n_jobs=-1, verbosity=-1)


def bilan(proba, y, montant, cout):
    alerte = proba * montant >= cout
    rate = (~alerte) & (y == 1)
    vraies = alerte & (y == 1)
    return {
        "cout_verification": cout,
        "alertes": int(alerte.sum()),
        "fraudes": int(y.sum()),
        "fraudes_detectees": int(vraies.sum()),
        "rappel": round(vraies.sum() / max(y.sum(), 1), 4),
        "precision": round(vraies.sum() / max(alerte.sum(), 1), 4),
        "montant_fraude_detecte_pct": round(100 * montant[vraies].sum() / montant[y == 1].sum(), 2),
        "cout_total": round(float(montant[rate].sum() + cout * alerte.sum())),
        "cout_sans_modele": round(float(montant[y == 1].sum())),
    }


# 1. Prédictions hors pli
hors_pli = np.full(len(y), np.nan)
pli_de = np.zeros(len(y), dtype=int)
for k, (i_ent, i_val) in enumerate(plis_temporels(steps), start=1):
    hors_pli[i_val] = nouveau_modele().fit(X[i_ent], y[i_ent]).predict_proba(X[i_val])[:, 1]
    pli_de[i_val] = k
    print(f"Pli {k} prédit")

apprentissage = (pli_de >= 1) & (pli_de <= 4)
controle = pli_de == 5

# 2. Calibration apprise sur les plis 1 à 4, vérifiée sur le pli 5
iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(hors_pli[apprentissage], y[apprentissage])
brut, calibre = hors_pli[controle], iso.predict(hors_pli[controle])
print()
print("Vérification sur le pli 5 (jamais vu par la calibration) :")
print(f"  Taux de fraude réel          : {y[controle].mean():.5f}")
print(f"  Probabilité moyenne brute    : {brut.mean():.5f}")
print(f"  Probabilité moyenne calibrée : {calibre.mean():.5f}")
print(f"  Brier brut    : {brier_score_loss(y[controle], brut):.6f}")
print(f"  Brier calibré : {brier_score_loss(y[controle], calibre):.6f}")
print(f"  PR-AUC brute / calibrée : {average_precision_score(y[controle], brut):.4f} / "
      f"{average_precision_score(y[controle], calibre):.4f}")

tranches = [0, 0.001, 0.01, 0.05, 0.2, 0.5, 1.0001]
lignes = []
for bas, haut in zip(tranches[:-1], tranches[1:]):
    dans = (calibre >= bas) & (calibre < haut)
    if dans.sum():
        lignes.append({"tranche": f"{bas}-{min(haut, 1)}", "transactions": int(dans.sum()),
                       "proba_moyenne": round(float(calibre[dans].mean()), 4),
                       "taux_fraude_observe": round(float(y[controle][dans].mean()), 4)})
print()
print("Fiabilité des probabilités calibrées (pli 5) :")
print(pl.DataFrame(lignes))

# 3. Règle de décision et sensibilité au coût, sur le pli 5
sensibilite = pl.DataFrame([bilan(calibre, y[controle], montant[controle], c) for c in SENSIBILITE])
print()
print("Règle « alerter si probabilité × montant ≥ coût d'une vérification » (pli 5) :")
print(sensibilite)

# 4. Modèle final : tout le développement ; calibration sur toutes les prédictions hors pli
modele = nouveau_modele().fit(X, y)
connu = pli_de > 0
calibrateur = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(hors_pli[connu], y[connu])

Path("models").mkdir(exist_ok=True)
joblib.dump({"modele": modele, "calibrateur": calibrateur, "variables": VARIABLES,
             "cout_verification": COUT_VERIFICATION}, "models/modele_final.joblib")
Path("reports").mkdir(exist_ok=True)
sensibilite.write_csv("reports/sensibilite_cout_pli5.csv")
pl.DataFrame(lignes).write_csv("reports/fiabilite_pli5.csv")

importances = sorted(zip(VARIABLES, modele.booster_.feature_importance("gain")), key=lambda t: -t[1])
print()
print("Importance des variables (gain) :")
for nom, gain in importances:
    print(f"  {nom:<25} {gain:,.0f}")
print()
print("Modèle final enregistré : models/modele_final.joblib")
