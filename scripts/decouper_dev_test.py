"""Découpe paysim.parquet en jeu de développement et jeu de test (décision D9)."""

import hashlib
from pathlib import Path

import duckdb

SOURCE = Path("data/interim/paysim.parquet")
DOSSIER = Path("data/processed")
DEV = DOSSIER / "developpement.parquet"
TEST = DOSSIER / "test.parquet"
DERNIER_STEP_DEV = 355  # D9 : premier step où le cumul atteint 80 %


def empreinte_sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def valeur(con, requete):
    return con.execute(requete).fetchone()[0]


def main():
    # 1. Ne jamais écraser un découpage existant
    for fichier in (DEV, TEST):
        if fichier.exists():
            raise SystemExit(f"{fichier} existe déjà : on ne réécrit jamais le jeu de test.")
    DOSSIER.mkdir(parents=True, exist_ok=True)

    # 2. Découpage selon le temps uniquement
    con = duckdb.connect()
    con.execute(f"CREATE VIEW source AS SELECT * FROM read_parquet('{SOURCE}')")
    con.execute(f"COPY (SELECT * FROM source WHERE step <= {DERNIER_STEP_DEV}) TO '{DEV}' (FORMAT parquet)")
    con.execute(f"COPY (SELECT * FROM source WHERE step > {DERNIER_STEP_DEV}) TO '{TEST}' (FORMAT parquet)")
    con.execute(f"CREATE VIEW dev AS SELECT * FROM read_parquet('{DEV}')")
    con.execute(f"CREATE VIEW test AS SELECT * FROM read_parquet('{TEST}')")

    # 3. Contrôles (aucun ne regarde isFraud)
    n_source = valeur(con, "SELECT COUNT(*) FROM source")
    n_dev = valeur(con, "SELECT COUNT(*) FROM dev")
    n_test = valeur(con, "SELECT COUNT(*) FROM test")
    step_max = valeur(con, "SELECT MAX(step) FROM source")
    dev_min, dev_max = con.execute("SELECT MIN(step), MAX(step) FROM dev").fetchone()
    test_min, test_max = con.execute("SELECT MIN(step), MAX(step) FROM test").fetchone()
    somme = "SELECT SUM(CAST(amount AS DECIMAL(18,2))) FROM {}"
    manquantes = valeur(con, """
        SELECT COUNT(*) FROM (
            SELECT * FROM source
            EXCEPT ALL
            (SELECT * FROM dev UNION ALL SELECT * FROM test)
        )""")
    en_trop = valeur(con, """
        SELECT COUNT(*) FROM (
            (SELECT * FROM dev UNION ALL SELECT * FROM test)
            EXCEPT ALL
            SELECT * FROM source
        )""")

    controles = {
        "lignes : dev + test = source": n_dev + n_test == n_source,
        "steps du dev : 1 à 355": (dev_min, dev_max) == (1, DERNIER_STEP_DEV),
        f"steps du test : 356 à {step_max}": (test_min, test_max) == (DERNIER_STEP_DEV + 1, step_max),
        "montants : dev + test = source": valeur(con, somme.format("dev")) + valeur(con, somme.format("test"))
        == valeur(con, somme.format("source")),
        "aucune transaction perdue": manquantes == 0,
        "aucune transaction en double ou inventée": en_trop == 0,
    }

    print(f"Développement : {n_dev:,} transactions ({100 * n_dev / n_source:.2f} %)")
    print(f"Test          : {n_test:,} transactions ({100 * n_test / n_source:.2f} %)")
    for nom, ok in controles.items():
        print(f"[{'OK' if ok else 'ÉCHEC'}] {nom}")
    con.close()

    # 4. Scellement, seulement si tout est bon
    if not all(controles.values()):
        DEV.unlink()
        TEST.unlink()
        raise SystemExit("Contrôles en échec : fichiers supprimés, rien n'est scellé.")
    TEST.chmod(0o444)
    print(f"Jeu de test scellé (lecture seule). Empreinte sha256 : {empreinte_sha256(TEST)}")


if __name__ == "__main__":
    main()