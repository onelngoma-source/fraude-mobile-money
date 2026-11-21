"""LightGBM : réglage des hyperparamètres par validation croisée temporelle (D10), suivi dans MLflow."""

import json
from pathlib import Path

import lightgbm as lgb
import mlflow
import numpy as np
import optuna
import polars as pl
from sklearn.metrics import average_precision_score

from validation import plis_temporels
from variables import VARIABLES

N_ESSAIS = 25

df = pl.read_parquet("data/processed/variables_dev.parquet").sort("step", maintain_order=True)
X = df.select(VARIABLES).to_numpy().astype(np.float32)
y = df["isFraud"].to_numpy()
steps = df["step"].to_numpy()
plis = list(plis_temporels(steps))


def evaluer(params: dict) -> list[float]:
    scores = []
    for i_ent, i_val in plis:
        modele = lgb.LGBMClassifier(**params, objective="binary", random_state=42, n_jobs=-1, verbosity=-1)
        modele.fit(X[i_ent], y[i_ent])
        proba = modele.predict_proba(X[i_val])[:, 1]
        scores.append(average_precision_score(y[i_val], proba))
    return scores


def objectif(essai: optuna.Trial) -> float:
    params = {
        "n_estimators": essai.suggest_int("n_estimators", 100, 600, step=100),
        "learning_rate": essai.suggest_float("learning_rate", 0.02, 0.2, log=True),
        "num_leaves": essai.suggest_int("num_leaves", 15, 127, log=True),
        "min_child_samples": essai.suggest_int("min_child_samples", 20, 500, log=True),
        "subsample": essai.suggest_float("subsample", 0.6, 1.0),
        "subsample_freq": 1,
        "colsample_bytree": essai.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_lambda": essai.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "scale_pos_weight": essai.suggest_float("scale_pos_weight", 1.0, 100.0, log=True),
    }
    with mlflow.start_run(run_name=f"essai_{essai.number}", nested=True):
        scores = evaluer(params)
        mlflow.log_params(params)
        for k, s in enumerate(scores, start=1):
            mlflow.log_metric(f"pr_auc_pli_{k}", s)
        mlflow.log_metric("pr_auc_moyenne", float(np.mean(scores)))
        mlflow.log_metric("pr_auc_ecart_type", float(np.std(scores)))
    essai.set_user_attr("scores", scores)
    print(f"Essai {essai.number + 1}/{N_ESSAIS} : PR-AUC moyenne {np.mean(scores):.4f}")
    return float(np.mean(scores))


mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("fraude-lightgbm")
optuna.logging.set_verbosity(optuna.logging.WARNING)

with mlflow.start_run(run_name="optimisation"):
    etude = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    etude.optimize(objectif, n_trials=N_ESSAIS)
    meilleur = etude.best_trial
    mlflow.log_params({f"meilleur_{k}": v for k, v in meilleur.params.items()})
    mlflow.log_metric("meilleure_pr_auc_moyenne", meilleur.value)

scores = meilleur.user_attrs["scores"]
print()
print("Meilleurs hyperparamètres :", meilleur.params)
print("PR-AUC par pli :", [round(s, 4) for s in scores])
print(f"PR-AUC moyenne : {np.mean(scores):.4f} (écart-type {np.std(scores):.4f})")
print("Rappel, régression logistique : 0.1051 (écart-type 0.0813)")

Path("reports").mkdir(exist_ok=True)
params_finaux = {**meilleur.params, "subsample_freq": 1}
Path("reports/meilleurs_parametres_lightgbm.json").write_text(json.dumps(params_finaux, indent=2))
pl.DataFrame({"pli": list(range(1, 6)), "pr_auc": scores}).write_csv("reports/lightgbm_cv.csv")
