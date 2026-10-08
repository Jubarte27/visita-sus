import random
from dataclasses import replace

import pytest

from engine import alns, greedy
from engine.alns import ALNS, RouteState
from engine.evaluation import evaluate, timing
from engine.instance import Params
from tests.engine.test_greedy import random_instance

FAST = Params(beta=30, gamma=2, iterations=150, time_limit_s=60, seeds=[0, 1, 2])


@pytest.mark.parametrize("seed", range(15))
def test_insercao_em_o1_bate_com_o_cronograma(seed):
    inst = random_instance(seed)
    rng = random.Random(seed)
    route = greedy.solve(inst, FAST).route
    state = RouteState(inst, route)
    H0, walk0, _ = timing(inst, route)
    assert state.H == pytest.approx(H0) and state.walk == pytest.approx(walk0)
    outside = [c for c in inst.candidates if c not in route]
    for c in rng.sample(outside, min(8, len(outside))):
        for p in range(1, len(route)):
            H, walk, ok = timing(inst, route[:p] + [c] + route[p:])
            got = state.insertion(c, p)
            if ok and H <= inst.Tmax + 1e-9:
                assert got is not None, (c, p)
                assert got[0] == pytest.approx(walk - walk0) and got[1] == pytest.approx(H - H0)
            else:
                assert got is None, (c, p)


@pytest.mark.parametrize("seed", range(10))
def test_viavel_e_nunca_pior_que_o_guloso(seed):
    inst = random_instance(seed)
    g = greedy.solve(inst, FAST)
    a = alns.solve(inst, FAST, seed=seed)
    assert a.feasible, a.violations
    assert a.objective <= g.objective + 1e-9
    assert a.objective == pytest.approx(evaluate(inst, FAST, a.route).objective)
    inner = a.route[1:-1]
    assert sorted(inner[:len(inst.urgent)]) == inst.urgent
    assert sorted(inner + [i for i, _ in a.unvisited]) == list(inst.candidates)
    assert a.method == "alns" and a.seed == seed


def test_melhora_o_guloso_em_alguma_instancia():
    ganhos = [greedy.solve(random_instance(s), FAST).objective - alns.solve(random_instance(s), FAST).objective
              for s in range(10)]
    assert max(ganhos) > 1e-6


def test_mesma_semente_mesmo_resultado():
    inst = random_instance(4)
    a = alns.solve(inst, FAST, seed=7)
    b = alns.solve(inst, FAST, seed=7)
    assert a.route == b.route and a.objective == b.objective


def test_respeita_o_tempo_limite():
    inst = random_instance(2, n=60)
    params = replace(FAST, iterations=10**9, time_limit_s=0.3)
    sol = alns.solve(inst, params)
    assert sol.runtime_s < 0.3 + 0.5  # guloso + uma iteração além do prazo


def test_varias_sementes():
    inst = random_instance(5)
    sol = alns.solve_multi_seed(inst, FAST)
    st = sol.seeds_stats
    assert st["sementes"] == [0, 1, 2] and len(st["objetivos"]) == 3
    assert sol.objective == st["melhor"] == min(st["objetivos"])
    assert st["pior"] >= st["media"] >= st["melhor"] and st["desvio"] >= 0
    assert sol.seed in (0, 1, 2)


def test_sanitizacao_poe_urgentes_no_inicio(inst):
    s = ALNS(inst, FAST, 0)
    assert s.sanitize([0, 1, 2, 3, 0]) == [0, 2, 1, 3, 0]


def test_instancia_a_mao(inst):
    # na instância à mão o guloso já é ótimo para β=30, γ=2 (rota [0, 2, 1, 0], objetivo 76)
    sol = alns.solve(inst, FAST)
    assert sol.route == [0, 2, 1, 0] and sol.objective == pytest.approx(76)


def test_sem_candidatas_nao_urgentes(inst):
    inst.visits = inst.visits[:3]
    inst.t = inst.t[:3, :3]
    inst.visits[1].urgent = True
    sol = alns.solve(inst, FAST)
    assert sol.feasible and sorted(sol.route[1:-1]) == [1, 2]
