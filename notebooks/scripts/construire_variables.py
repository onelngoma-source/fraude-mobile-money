"""Calcule les variables sur le jeu de développement et les contrôle."""

import duckdb

from variables import VARIABLES, requete_variables

DEV = "data/processed/developpement.parquet"
SORTIE = "data/processed/variables_dev.parquet"

con = duckdb.connect()
requete = requete_variables(f"read_parquet('{DEV}')")
con.execute(f"COPY ({requete} ORDER BY step) TO '{SORTIE}' (FORMAT parquet)")
con.execute(f"CREATE VIEW v AS SELECT * FROM read_parquet('{SORTIE}')")

lignes, fraudes = con.execute("SELECT COUNT(*), SUM(isFraud) FROM v").fetchone()
manquants = con.execute(
    "SELECT " + " + ".join(f"COUNT(*) - COUNT({c})" for c in VARIABLES) + " FROM v"
).fetchone()[0]

print(f"[{'OK' if lignes == 2_238_469 else 'ÉCHEC'}] lignes : {lignes:,} (attendu 2,238,469)")
print(f"[{'OK' if fraudes == 3963 else 'ÉCHEC'}] fraudes : {fraudes} (attendu 3963)")
print(f"[{'OK' if manquants == 0 else 'ÉCHEC'}] valeurs manquantes : {manquants}")
print()
print("Moyenne de chaque variable, transactions normales (0) et fraudes (1) :")
print(con.sql(
    "SELECT isFraud, " + ", ".join(f"ROUND(AVG({c}), 3) AS {c}" for c in VARIABLES)
    + " FROM v GROUP BY isFraud ORDER BY isFraud"
).pl())