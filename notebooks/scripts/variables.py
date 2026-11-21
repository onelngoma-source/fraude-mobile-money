"""Variables du modèle : uniquement des informations connues au moment de la transaction (D6)."""

VARIABLES = [
    "est_transfer",
    "heure",
    "log_montant",
    "montant_10m",
    "orig_nb_avant",
    "dest_nb_avant",
    "dest_nb_24h",
    "log_dest_montant_avant",
]


def requete_variables(source: str) -> str:
    """Requête SQL qui calcule les variables à partir d'une table de transactions.

    L'historique des comptes est calculé sur tous les types de transactions,
    puis on ne garde que le périmètre TRANSFER et CASH_OUT (D14).
    Les fenêtres s'arrêtent au step précédent : jamais d'information du présent ni du futur.
    """
    return f"""
    WITH historique AS (
        SELECT
            *,
            COUNT(*) OVER (PARTITION BY nameOrig ORDER BY step
                RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS orig_nb_avant,
            COUNT(*) OVER (PARTITION BY nameDest ORDER BY step
                RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS dest_nb_avant,
            COUNT(*) OVER (PARTITION BY nameDest ORDER BY step
                RANGE BETWEEN 24 PRECEDING AND 1 PRECEDING) AS dest_nb_24h,
            COALESCE(SUM(amount) OVER (PARTITION BY nameDest ORDER BY step
                RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS dest_montant_avant
        FROM {source}
    )
    SELECT
        step,
        type,
        isFraud,
        CAST(type = 'TRANSFER' AS INTEGER) AS est_transfer,
        (step - 1) % 24 AS heure,
        LN(1 + amount) AS log_montant,
        CAST(ABS(amount - 10000000) < 0.01 AS INTEGER) AS montant_10m,
        orig_nb_avant,
        dest_nb_avant,
        dest_nb_24h,
        LN(1 + dest_montant_avant) AS log_dest_montant_avant
    FROM historique
    WHERE type IN ('TRANSFER', 'CASH_OUT')
    """