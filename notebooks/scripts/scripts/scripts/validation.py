"""Validation croisée temporelle à l'intérieur du jeu de développement (D10)."""

import numpy as np


def plis_temporels(steps: np.ndarray, n_blocs: int = 6):
    """Découpe des données triées par step en n_blocs consécutifs de taille proche.

    Pli k : entraînement sur les blocs 1 à k, validation sur le bloc k + 1.
    Les coupures tombent toujours entre deux steps.
    """
    n = len(steps)
    bornes = [0]
    for k in range(1, n_blocs):
        i = int(n * k / n_blocs)
        bornes.append(int(np.searchsorted(steps, steps[i], side="right")))
    bornes.append(n)
    for k in range(1, n_blocs):
        yield np.arange(0, bornes[k]), np.arange(bornes[k], bornes[k + 1])