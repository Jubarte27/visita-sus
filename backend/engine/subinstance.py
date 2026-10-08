"""Subinstâncias pequenas de uma instância real, para comparar a ALNS com o MILP (referência exata)."""

import numpy as np

from .instance import Instance


def subinstance(inst: Instance, n: int, seed: int = 0) -> Instance:
    """
    UBS + n candidatas sorteadas (sem reposição) da instância, preservando a ordem original (urgentes primeiro).
    Um subconjunto das urgentes continua cabendo na jornada, pois o conjunto inteiro cabia (pré-processamento).
    """
    cands = list(inst.candidates)
    if n >= len(cands):
        chosen = cands
    else:
        chosen = sorted(np.random.default_rng(seed).choice(cands, size=n, replace=False).tolist())
    idx = [0, *chosen]
    return Instance(visits=[inst.visits[i] for i in idx], t=inst.t[np.ix_(idx, idx)], T=inst.T, Tmax=inst.Tmax,
                    K=inst.K)
