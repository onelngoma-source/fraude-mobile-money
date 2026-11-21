"""Prédiction pour une transaction : mêmes variables qu'à l'entraînement (scripts/variables.py)."""

import math
import os

import joblib
import numpy as np

PERIMETRE = {"TRANSFER", "CASH_OUT"}


def variables_transaction(t: dict) -> dict:
    """Calcule en Python les variables définies en SQL dans scripts/variables.py."""
    return {
        "est_transfer": 1.0 if t["type"] == "TRANSFER" else 0.0,
        "heure": float((t["step"] - 1) % 24),
        "log_montant": math.log1p(t["montant"]),
        "montant_10m": 1.0 if abs(t["montant"] - 10_000_000) < 0.01 else 0.0,
        "orig_nb_avant": float(t["orig_nb_avant"]),
        "dest_nb_avant": float(t["dest_nb_avant"]),
        "dest_nb_24h": float(t["dest_nb_24h"]),
        "log_dest_montant_avant": math.log1p(t["dest_montant_avant"]),
    }


class Predicteur:
    def __init__(self, chemin: str | None = None):
        art = joblib.load(chemin or os.environ.get("MODELE_CHEMIN", "models/modele_final.joblib"))
        self.modele = art["modele"]
        self.calibrateur = art["calibrateur"]
        self.variables = art["variables"]
        self.cout_verification = art["cout_verification"]

    def predire(self, t: dict) -> dict:
        if t["type"] not in PERIMETRE:
            return {"dans_perimetre": False, "probabilite_fraude": 0.0, "perte_attendue": 0.0,
                    "alerte": False, "cout_verification": self.cout_verification}
        valeurs = variables_transaction(t)
        X = np.array([[valeurs[v] for v in self.variables]], dtype=np.float32)
        brut = float(self.modele.predict_proba(X)[0, 1])
        proba = float(self.calibrateur.predict([brut])[0])
        perte = proba * t["montant"]
        return {"dans_perimetre": True, "probabilite_fraude": round(proba, 6),
                "perte_attendue": round(perte, 2), "alerte": perte >= self.cout_verification,
                "cout_verification": self.cout_verification}
