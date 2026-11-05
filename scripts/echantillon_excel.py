"""Crée un échantillon lisible des données dans un fichier Excel, sans modifier les données brutes."""

import polars as pl
from xlsxwriter import Workbook

SOURCE = "data/raw/PS_20174392719_1491204439457_log.csv"
SORTIE = "/mnt/c/Users/oneln/Downloads/paysim_echantillon.xlsx"

donnees = pl.scan_csv(SOURCE)
premieres = donnees.head(1000).collect()
fraudes = donnees.filter(pl.col("isFraud") == 1).collect().sample(n=500, seed=42).sort("step")
normales = donnees.filter(pl.col("isFraud") == 0).collect().sample(n=1000, seed=42).sort("step")

with Workbook(SORTIE) as classeur:
    premieres.write_excel(classeur, worksheet="1000 premieres lignes", autofit=True)
    fraudes.write_excel(classeur, worksheet="500 fraudes au hasard", autofit=True)
    normales.write_excel(classeur, worksheet="1000 normales au hasard", autofit=True)

print("Fichier créé :", SORTIE)