"""Démo : détection de fraude mobile money."""

import json
import sys
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))
from fraude_mobile_money.predicteur import Predicteur  # noqa: E402

st.set_page_config(page_title="Détection de fraude mobile money", page_icon="🔎", layout="wide")


@st.cache_resource
def charger_predicteur():
    return Predicteur(str(RACINE / "models" / "modele_final.joblib"))


@st.cache_data
def charger_rapport():
    return json.loads((RACINE / "reports" / "evaluation_finale.json").read_text())


predicteur = charger_predicteur()
rapport = charger_rapport()
glob = next(r for r in rapport["resultats"] if r["periode"] == "global")

st.title("Détection de fraude mobile money")
st.caption("6,3 millions de transactions simulées (PaySim). Modèle LightGBM calibré, "
           "évalué une seule fois sur un jeu de test scellé couvrant les 16 derniers jours.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Fraudes détectées", f"{100 * glob['rappel']:.0f} %")
c2.metric("Montant fraudé détecté", f"{glob['montant_fraude_detecte_pct']:.0f} %")
c3.metric("Réduction du coût", f"{glob['reduction_cout_pct']:.0f} %")
c4.metric("PR-AUC", f"{glob['pr_auc']:.2f}", f"hasard : {glob['pr_auc_hasard']:.3f}", delta_color="off")

tester, resultats, methode = st.tabs(["Tester une transaction", "Résultats sur le jeu de test", "Méthode et limites"])

with tester:
    gauche, droite = st.columns(2)
    with gauche:
        type_ = st.selectbox("Type de transaction", ["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"])
        heure = st.slider("Heure de la transaction", 0, 23, 3)
        montant = st.number_input("Montant", min_value=1.0, value=250_000.0, step=10_000.0)
        orig_nb = st.number_input("Opérations déjà faites par l'émetteur", min_value=0, value=0, step=1)
    with droite:
        dest_nb = st.number_input("Réceptions déjà faites par le destinataire", min_value=0, value=0, step=1)
        dest_24 = st.number_input("Dont sur les dernières 24 heures", min_value=0, max_value=int(dest_nb),
                                  value=0, step=1)
        dest_mt = st.number_input("Montant déjà reçu par le destinataire", min_value=0.0, value=0.0,
                                  step=10_000.0)
        cout = st.select_slider("Coût d'une vérification", options=[1_000, 5_000, 20_000, 50_000], value=5_000)

    r = predicteur.predire({"type": type_, "step": heure + 1, "montant": montant, "orig_nb_avant": orig_nb,
                            "dest_nb_avant": dest_nb, "dest_nb_24h": dest_24, "dest_montant_avant": dest_mt})
    st.divider()
    if not r["dans_perimetre"]:
        st.info("Hors périmètre : le modèle ne traite que les TRANSFER et CASH_OUT, "
                "les seuls types où la fraude apparaît dans les données.")
    else:
        perte = r["probabilite_fraude"] * montant
        a, b, c = st.columns(3)
        a.metric("Probabilité de fraude (calibrée)", f"{100 * r['probabilite_fraude']:.2f} %")
        b.metric("Perte attendue", f"{perte:,.0f}".replace(",", " "))
        c.metric("Coût d'une vérification", f"{cout:,}".replace(",", " "))
        if perte >= cout:
            st.error("Alerte : la perte attendue dépasse le coût d'une vérification. Transaction à contrôler.")
        else:
            st.success("Pas d'alerte : vérifier coûterait plus cher que la perte attendue.")
    st.caption("Règle de décision : alerter si probabilité × montant ≥ coût d'une vérification. "
               "Dans un système réel, l'historique des comptes serait fourni par une base de données.")

with resultats:
    noms = {"global": "Tout le test", "periode_chargee": "Période chargée", "periode_calme": "Période calme"}
    st.subheader("Résultats par période (coût d'une vérification : 5 000)")
    st.dataframe([{
        "Période": noms[x["periode"]], "Steps": x["steps"], "Transactions": x["transactions"],
        "Fraudes": x["fraudes"], "PR-AUC": x["pr_auc"], "Rappel": f"{100 * x['rappel']:.1f} %",
        "Précision": f"{100 * x['precision']:.1f} %",
        "Montant fraudé détecté": f"{x['montant_fraude_detecte_pct']} %",
        "Réduction du coût": f"{x['reduction_cout_pct']} %",
    } for x in rapport["resultats"]], hide_index=True)
    st.subheader("Sensibilité au coût d'une vérification")
    st.dataframe([{
        "Coût d'une vérification": x["cout_verification"], "Alertes": x["alertes"],
        "Rappel": f"{100 * x['rappel']:.1f} %", "Précision": f"{100 * x['precision']:.1f} %",
        "Montant fraudé détecté": f"{x['montant_fraude_detecte_pct']} %",
        "Réduction du coût": f"{x['reduction_cout_pct']} %",
    } for x in rapport["sensibilite"]], hide_index=True)
    st.caption("La précision dépend du taux de fraude : 0,07 % en période chargée, 0,97 % en période calme. "
               "Le même modèle obtient donc 5 % de précision dans un cas et 33 % dans l'autre.")

with methode:
    st.markdown("""
**Ce qui rend l'évaluation fiable**
- Découpage **dans l'ordre du temps** : le modèle apprend sur les jours 1 à 15 et il est évalué sur les jours 15 à 31.
- Jeu de test **scellé** (lecture seule, empreinte sha256) et ouvert **une seule fois**, à la fin.
- **Aucune colonne de solde** : la documentation de PaySim indique qu'elles ont été modifiées après la détection des fraudes, ce qui fausserait les scores.
- Hyperparamètres réglés par **validation croisée temporelle** (5 plis) avec Optuna, essais suivis dans MLflow.
- **Probabilités calibrées** (régression isotonique), puis **seuil fixé par les coûts** avec analyse de sensibilité.
- Évaluation sur **tout** le test, y compris les types de transactions non traités par le modèle.

**Limites**
- Données **simulées** : la variable la plus utile, l'heure, l'est surtout parce que le simulateur répartit les fraudes uniformément sur 24 heures.
- Le taux de fraude change entre les périodes : les probabilités sont bien calibrées en période chargée et sous-estimées d'environ 2 fois en période calme.
- Les probabilités les plus extrêmes (jusqu'à 100 %) viennent du palier supérieur de la calibration : à lire comme « risque très élevé ».
""")
