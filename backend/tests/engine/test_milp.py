from itertools import combinations, permutations

import pytest

from engine import alns, greedy, milp
from engine.evaluation import evaluate
from engine.instance import Params
from engine.subinstance import subinstance
from tests.engine.test_greedy import random_instance

PARAMS = Params(beta=30, gamma=2, iterations=200, seeds=[0])


def forca_bruta(inst, params) -> float:
    """Melhor objetivo viável enumerando subconjuntos e ordens (urgentes sempre, e primeiro)."""
    U = inst.urgent
    R = [i for i in inst.candidates if i not in U]
    best = float("inf")
    for pu in permutations(U):
        for k in range(len(R) + 1):
            for sub in combinations(R, k):
                for pr in permutations(sub):
                    ev = evaluate(inst, params, [0, *pu, *pr, 0])
                    if ev.feasible and ev.objective < best:
                        best = ev.objective
    return best


def test_instancia_a_mao(inst):
    sol = milp.solve(inst, PARAMS)
    assert sol.route == [0, 2, 1, 0] and sol.objective == pytest.approx(76) and sol.gap == pytest.approx(0)
    assert sol.method == "milp" and sol.feasible


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("n", [6, 7])
def test_bate_com_a_forca_bruta(seed, n):
    # jornada curta para que nem tudo caiba e a escolha das visitas importe
    inst = random_instance(seed, n=n, Tmax=110, K=1)
    sol = milp.solve(inst, PARAMS, time_limit_s=30)
    assert sol.feasible, sol.violations
    assert sol.objective == pytest.approx(forca_bruta(inst, PARAMS), abs=1e-6)
    assert sol.gap is not None and sol.gap < 1e-6


@pytest.mark.parametrize("seed", range(4))
def test_heuristicas_nunca_abaixo_do_otimo(seed):
    inst = random_instance(seed, n=9, Tmax=150, K=1)
    ref = milp.solve(inst, PARAMS, time_limit_s=30)
    assert ref.gap == pytest.approx(0, abs=1e-6)
    for sol in (greedy.solve(inst, PARAMS), alns.solve(inst, PARAMS)):
        assert sol.objective >= ref.objective - 1e-6


def test_subinstancia():
    inst = random_instance(3, n=30)
    sub = subinstance(inst, 10, seed=1)
    assert sub.n == 11 and sub.visits[0] is inst.visits[0] and sub.t.shape == (11, 11)
    ids = [v.id for v in sub.visits[1:]]
    assert ids == sorted(ids) and len(set(ids)) == 10
    i, j = 1, 2
    assert sub.t[i, j] == inst.t[ids[0], ids[1]]  # ids = índices na instância original (random_instance usa id = i)
    assert subinstance(inst, 10, seed=1).visits == sub.visits  # determinística
    assert subinstance(inst, 100).n == inst.n
