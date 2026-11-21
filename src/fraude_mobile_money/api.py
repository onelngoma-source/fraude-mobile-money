"""API de détection de fraude : POST /predire."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from fraude_mobile_money.predicteur import Predicteur


class Transaction(BaseModel):
    type: Literal["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"]
    step: int = Field(ge=1, description="Heure de la simulation (1 = première heure)")
    montant: float = Field(gt=0)
    orig_nb_avant: int = Field(0, ge=0, description="Opérations déjà faites par l'émetteur")
    dest_nb_avant: int = Field(0, ge=0, description="Réceptions déjà faites par le destinataire")
    dest_nb_24h: int = Field(0, ge=0, description="Réceptions du destinataire sur les 24 dernières heures")
    dest_montant_avant: float = Field(0, ge=0, description="Montant déjà reçu par le destinataire")


app = FastAPI(title="Détection de fraude mobile money", version="1.0")
predicteur = Predicteur()


@app.get("/sante")
def sante():
    return {"statut": "ok"}


@app.post("/predire")
def predire(transaction: Transaction):
    return predicteur.predire(transaction.model_dump())
