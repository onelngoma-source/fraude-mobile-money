"""Évaluation finale sur le jeu de test. Exécutée une seule fois (D12)."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import duckdb
import joblib
import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss

from variables import requete_variables

DEV = "data/processed/developpement.parquet"
TEST = Path("data/processed/test.parquet")
EMPREINTE_TEST = "220c6c02cbf6ca807a43a95ac443e99a1aa4bdeef60b03408d3553624b344e36"
RAPPORT = Path("reports/evaluation_finale.json")
PERIODES = {"global": (356, 743), "periode_chargee": (356, 408), "periode_calme": (409, 743)}
SENSIBILITE = [1_000, 5_000, 20_000, 50_000]

# 1. Garde-fous
if RAPPORT.exists():
    raise SystemExit("L'évaluation finale a déjà été faite : le jeu de test ne s'utilise qu'une fois.")
h = hashlib.sha256()
with open(TEST, "rb") as f:
    for bloc in iter(lambda: f.read(1024 * 1024), b""):
        h.update(bloc)
if h.hexdigest() != EMPREINTE_TEST:
    raise SystemExit("Empreinte du jeu de test différente de celle du scellement : arrêt.")
print("[OK] Empreinte du jeu de test conforme au scellement (D12)")

# 2. Variables avec l'historique complet, transactions du test uniquement
art = joblib.load("models/modele_final.joblib")
con = duckdb.connect()
source = f"(SELECT * FROM read_parquet('{DEV}') UNION ALL SELECT * FROM read_parquet('{TEST}'))"
dans = con.sql(f"SELECT * FROM ({requete_variables(source)}) WHERE step > 355").pl()
hors = con.sql(
    f"SELECT step, isFraud, amount FROM read_parquet('{TEST}') WHERE type NOT IN ('TRANSFER', 'CASH_OUT')"
).pl()
total = len(dans) + len(hors)
print(f"[{'OK' if total == 1_248_736 else 'ÉCHEC'}] transactions du test : {total:,} "
      f"(périmètre {len(dans):,}, hors périmètre {len(hors):,})")

X = dans.select(art["variables"]).to_numpy().astype(np.float32)
brut = art["modele"].predict_proba(X)[:, 1]
calibre = art["calibrateur"].predict(brut)

# 3. Tout le test : les transactions hors périmètre ont une probabilité de 0 (D14)
step = np.concatenate([dans["step"].to_numpy(), hors["step"].to_numpy()])
y = np.concatenate([dans["isFraud"].to_numpy(), hors["isFraud"].to_numpy()])
montant = np.concatenate([np.expm1(dans["log_montant"].to_numpy()), hors["amount"].to_numpy()])
score_brut = np.concatenate([brut, np.zeros(len(hors))])
proba = np.concatenate([calibre, np.zeros(len(hors))])
perimetre = np.concatenate([np.ones(len(dans), bool), np.zeros(len(hors), bool)])


def mesures(nom, debut, fin, cout):
    m = (step >= debut) & (step <= fin)
    yy, mm, pp = y[m], montant[m], proba[m]
    alerte = pp * mm >= cout
    vraies = alerte & (yy == 1)
    ratees = (~alerte) & (yy == 1)
    cout_total = float(mm[ratees].sum() + cout * alerte.sum())
    cout_sans = float(mm[yy == 1].sum())
    p_in = m & perimetre
    return {
        "periode": nom,
        "steps": f"{debut}-{fin}",
        "cout_verification": cout,
        "transactions": int(m.sum()),
        "fraudes": int(yy.sum()),
        "fraudes_hors_perimetre": int((yy[~perimetre[m]] == 1).sum()),
        "taux_fraude_pct": round(100 * yy.mean(), 3),
        "pr_auc": round(float(average_precision_score(yy, score_brut[m])), 4),
        "pr_auc_hasard": round(float(yy.mean()), 4),
        "alertes": int(alerte.sum()),
        "fraudes_detectees": int(vraies.sum()),
        "rappel": round(vraies.sum() / max(yy.sum(), 1), 4),
        "precision": round(vraies.sum() / max(alerte.sum(), 1), 4),
        "montant_fraude_detecte_pct": round(100 * mm[vraies].sum() / max(cout_sans, 1), 2),
        "cout_total": round(cout_total),
        "cout_sans_modele": round(cout_sans),
        "reduction_cout_pct": round(100 * (1 - cout_total / max(cout_sans, 1)), 2),
        "proba_moyenne_calibree_perimetre": round(float(proba[p_in].mean()), 5),
        "taux_fraude_reel_perimetre": round(float(y[p_in].mean()), 5),
        "brier_perimetre": round(float(brier_score_loss(y[p_in], proba[p_in])), 6),
    }


resultats = [mesures(nom, d, f, 5_000) for nom, (d, f) in PERIODES.items()]
sensibilite = [mesures("global", 356, 743, c) for c in SENSIBILITE]

for r in resultats:
    print()
    print(f"=== {r['periode']} (steps {r['steps']}) ===")
    for cle, valeur in r.items():
        if cle not in ("periode", "steps"):
            print(f"  {cle:<35} {valeur}")

print()
print("=== Sensibilité au coût d'une vérification (global) ===")
for r in sensibilite:
    print(f"  coût {r['cout_verification']:>6} : rappel {r['rappel']:.3f}, précision {r['precision']:.3f}, "
          f"montant détecté {r['montant_fraude_detecte_pct']} %, réduction du coût {r['reduction_cout_pct']} %")

RAPPORT.write_text(json.dumps({
    "date": datetime.now().isoformat(timespec="seconds"),
    "empreinte_test": EMPREINTE_TEST,
    "resultats": resultats,
    "sensibilite": sensibilite,
}, indent=2, ensure_ascii=False))
print()
print(f"Rapport enregistré : {RAPPORT}. Le jeu de test a servi : ne plus modifier le modèle.")
