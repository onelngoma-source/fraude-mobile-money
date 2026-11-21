"""Les variables calculées en Python (API) doivent être identiques à celles calculées en SQL (entraînement)."""

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from variables import VARIABLES, requete_variables  # noqa: E402

from fraude_mobile_money.predicteur import variables_transaction  # noqa: E402

TRANSACTIONS = [
    # step, type, amount, nameOrig, nameDest, isFraud
    (1, "PAYMENT", 500.0, "C1", "C9", 0),
    (3, "TRANSFER", 1200.0, "C2", "C9", 0),
    (30, "CASH_OUT", 800.0, "C3", "C9", 0),
    (40, "TRANSFER", 10_000_000.0, "C4", "C9", 1),
    (40, "CASH_OUT", 250.0, "C5", "C9", 0),
]


def test_python_identique_a_sql():
    con = duckdb.connect()
    con.execute("CREATE TABLE t (step INTEGER, type VARCHAR, amount DOUBLE, nameOrig VARCHAR, "
                "nameDest VARCHAR, isFraud TINYINT)")
    con.executemany("INSERT INTO t VALUES (?, ?, ?, ?, ?, ?)", TRANSACTIONS)
    lignes = con.sql(f"SELECT * FROM ({requete_variables('t')}) ORDER BY step, type").fetchall()
    noms = ["step", "type", "isFraud", *VARIABLES]
    for ligne in lignes:
        sql = dict(zip(noms, ligne))
        montant = next(a for s, ty, a, *_ in TRANSACTIONS if s == sql["step"] and ty == sql["type"])
        anterieures = [x for x in TRANSACTIONS if x[4] == "C9" and x[0] < sql["step"]]
        python = variables_transaction({
            "type": sql["type"], "step": sql["step"], "montant": montant,
            "orig_nb_avant": sql["orig_nb_avant"],
            "dest_nb_avant": len(anterieures),
            "dest_nb_24h": sum(1 for x in anterieures if x[0] >= sql["step"] - 24),
            "dest_montant_avant": sum(x[2] for x in anterieures),
        })
        for v in VARIABLES:
            assert python[v] == pytest.approx(sql[v]), f"{v} différent au step {sql['step']}"
