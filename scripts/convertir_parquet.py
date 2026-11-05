"""Convertit le fichier brut CSV en Parquet et prouve qu'aucune donnée n'a été perdue ni modifiée."""

import hashlib
import sys
from pathlib import Path

import duckdb

CSV = Path("data/raw/PS_20174392719_1491204439457_log.csv")
PARQUET = Path("data/interim/paysim.parquet")
EMPREINTE_ATTENDUE = "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b"

# Types déclarés explicitement plutôt que devinés automatiquement.
COLONNES = {
    "step": "INTEGER",
    "type": "VARCHAR",
    "amount": "DOUBLE",
    "nameOrig": "VARCHAR",
    "oldbalanceOrg": "DOUBLE",
    "newbalanceOrig": "DOUBLE",
    "nameDest": "VARCHAR",
    "oldbalanceDest": "DOUBLE",
    "newbalanceDest": "DOUBLE",
    "isFraud": "TINYINT",
    "isFlaggedFraud": "TINYINT",
}

LECTURE_CSV = f"read_csv('{CSV}', header = true, columns = {COLONNES})"
LECTURE_PARQUET = f"read_parquet('{PARQUET}')"


def empreinte_sha256(chemin: Path) -> str:
    """Calcule l'empreinte SHA-256 d'un fichier, morceau par morceau."""
    calcul = hashlib.sha256()
    with chemin.open("rb") as fichier:
        for morceau in iter(lambda: fichier.read(1024 * 1024), b""):
            calcul.update(morceau)
    return calcul.hexdigest()


def totaux_de_controle(con: duckdb.DuckDBPyConnection, source: str) -> dict:
    """Résume une source par des totaux qui doivent être identiques avant et après conversion."""
    valeurs_manquantes = " + ".join(f"(COUNT(*) - COUNT({nom}))" for nom in COLONNES)
    requete = f"""
        SELECT
            COUNT(*) AS lignes,
            SUM(CAST(amount AS DECIMAL(18, 2))) AS somme_montants,
            SUM(isFraud) AS fraudes,
            SUM(isFlaggedFraud) AS signalees,
            MIN(step) AS premier_step,
            MAX(step) AS dernier_step,
            COUNT(DISTINCT type) AS types,
            {valeurs_manquantes} AS valeurs_manquantes
        FROM {source}
    """
    ligne = con.execute(requete).fetchone()
    noms = [colonne[0] for colonne in con.description]
    return dict(zip(noms, ligne))


def main() -> None:
    print("1. Vérification de l'empreinte du fichier brut...")
    empreinte = empreinte_sha256(CSV)
    if empreinte != EMPREINTE_ATTENDUE:
        sys.exit(f"ARRÊT : l'empreinte ne correspond pas au journal ({empreinte}).")
    print("   OK, le fichier brut est identique à celui du journal.")

    con = duckdb.connect()

    print("2. Conversion en Parquet...")
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY (SELECT * FROM {LECTURE_CSV}) TO '{PARQUET}' (FORMAT parquet)")

    print("3. Comparaison des totaux de contrôle...")
    avant = totaux_de_controle(con, LECTURE_CSV)
    apres = totaux_de_controle(con, LECTURE_PARQUET)
    for nom in avant:
        statut = "OK" if avant[nom] == apres[nom] else "DIFFÉRENT"
        print(
            f"   {nom:<20} CSV = {avant[nom]!s:<22} Parquet = {apres[nom]!s:<22} {statut}"
        )
    if avant != apres:
        sys.exit("ARRÊT : les totaux de contrôle diffèrent.")

    print("4. Comparaison ligne par ligne...")
    (differences,) = con.execute(
        f"SELECT COUNT(*) FROM (SELECT * FROM {LECTURE_CSV} EXCEPT ALL SELECT * FROM {LECTURE_PARQUET})"
    ).fetchone()
    if differences:
        sys.exit(
            f"ARRÊT : {differences} lignes du CSV sont absentes ou modifiées dans le Parquet."
        )
    print("   OK, chaque ligne du CSV se retrouve à l'identique dans le Parquet.")

    taille_csv = CSV.stat().st_size / 1e6
    taille_parquet = PARQUET.stat().st_size / 1e6
    print(
        f"5. Terminé : {taille_csv:.0f} Mo en CSV, {taille_parquet:.0f} Mo en Parquet."
    )


if __name__ == "__main__":
    main()