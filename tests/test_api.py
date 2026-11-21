"""Tests de l'API."""

from fastapi.testclient import TestClient

from fraude_mobile_money.api import app

client = TestClient(app)
BASE = {"step": 400, "montant": 250_000.0, "orig_nb_avant": 0, "dest_nb_avant": 3,
        "dest_nb_24h": 1, "dest_montant_avant": 900_000.0}


def test_sante():
    assert client.get("/sante").json() == {"statut": "ok"}


def test_prediction_dans_le_perimetre():
    r = client.post("/predire", json={**BASE, "type": "TRANSFER"}).json()
    assert r["dans_perimetre"] is True
    assert 0.0 <= r["probabilite_fraude"] <= 1.0
    assert r["alerte"] == (r["perte_attendue"] >= r["cout_verification"])


def test_hors_perimetre_jamais_signale():
    r = client.post("/predire", json={**BASE, "type": "PAYMENT"}).json()
    assert r["dans_perimetre"] is False and r["alerte"] is False


def test_donnees_invalides_refusees():
    assert client.post("/predire", json={**BASE, "type": "TRANSFER", "montant": -5}).status_code == 422
