import numpy as np
import pytest

from engine import greedy
from engine.evaluation import evaluate, timing
from engine.instance import Instance, Params, Visit
from engine.io import instance_from_files
from tests.fixtures.mini_instance import write_mini_instance

PARAMS = Params(beta=30, gamma=2)


def random_instance(seed: int, n: int = 30, Tmax: float = 240, K: int = 2) -> Instance:
    """Pontos aleatórios num quadrado de 15 min de lado; urgentes sem janela, alguns com janela de turno."""
    rng = np.random.default_rng(seed)
    xy = rng.random((n + 1, 2)) * 15
    t = np.abs(xy[:, None, :] - xy[None, :, :]).sum(axis=2)  # distância de Manhattan em min
    visits = [Visit(id=-1, node=0, s=0, w=0, P=0, d=0, tw=(0, Tmax))]
    for i in range(1, n + 1):
        urgent = rng.random() < 0.1
        turno = 0 if urgent else rng.choice(3, p=[0.7, 0.15, 0.15])
        tw = [(0, Tmax), (0, Tmax / 2), (Tmax / 2, Tmax)][turno]
        P = int(rng.choice([7, 15, 30, 60]))
        visits.append(Visit(id=i, node=i, s=float(rng.choice([10, 15, 20, 30])), w=float(rng.integers(1, 6)), P=P,
                            d=int(rng.integers(0, 2 * P)), tw=tw, urgent=urgent, grave=rng.random() < 0.2))
    return Instance(visits=visits, t=t, T=Tmax - 60, Tmax=Tmax, K=K)


def test_instancia_a_mao(inst):
    # urgente 2 primeiro; 1 entra (melhora 59 min); 3 só caberia com 17 min de excesso e pioraria o objetivo;
    # 4 é grave e o teto (K=1) já foi atingido pela urgente grave 2
    sol = greedy.solve(inst, PARAMS)
    assert sol.route == [0, 2, 1, 0]
    assert sol.objective == pytest.approx(76) and sol.feasible
    assert sorted(sol.unvisited) == [(3, "nao_coube"), (4, "teto_graves")]
    assert sol.method == "guloso"


def test_teto_maior_libera_a_grave(inst):
    # com K=2 a grave 4 deixa de ser barrada pelo teto, mas com T=90 não cabe depois de 1 e 3
    # (razões maiores): o motivo passa a ser nao_coube
    inst.K, inst.T = 2, 90
    sol = greedy.solve(inst, PARAMS)
    assert sol.route == [0, 2, 3, 1, 0] and sol.feasible
    assert sol.unvisited == [(4, "nao_coube")]


@pytest.mark.parametrize("seed", range(20))
def test_solucoes_aleatorias(seed):
    inst = random_instance(seed)
    sol = greedy.solve(inst, PARAMS)
    inner = sol.route[1:-1]
    assert sol.feasible, sol.violations
    # urgentes todas presentes e no início
    n_urg = len(inst.urgent)
    assert sorted(inner[:n_urg]) == inst.urgent
    # teto de graves (D6)
    graves = [i for i in inner if inst.visits[i].grave]
    assert len(graves) <= max(inst.K, sum(inst.visits[i].urgent for i in graves))
    # cada inserção melhora o objetivo: nunca pior que só as urgentes
    assert sol.objective <= evaluate(inst, PARAMS, greedy.urgent_route(inst)).objective + 1e-9
    # todas as candidatas aparecem uma vez: na rota ou como não atendidas
    assert sorted(inner + [i for i, _ in sol.unvisited]) == list(inst.candidates)


@pytest.mark.parametrize("seed", range(5))
def test_deterministico(seed):
    a = greedy.solve(random_instance(seed), PARAMS)
    b = greedy.solve(random_instance(seed), PARAMS)
    assert a.route == b.route and a.objective == b.objective


def test_nenhuma_candidata_que_falta_cabe_com_ganho():
    # depois do guloso, nenhuma candidata de fora pode ser inserida melhorando o objetivo
    inst = random_instance(3)
    sol = greedy.solve(inst, PARAMS)
    first = len(inst.urgent) + 1
    graves = sum(inst.visits[i].grave for i in sol.route)
    limit = greedy.graves_limit(inst, sol.route)
    for c, _ in sol.unvisited:
        if inst.visits[c].grave and graves >= limit:
            continue
        for p in range(first, len(sol.route)):
            r = sol.route[:p] + [c] + sol.route[p:]
            H, _, ok = timing(inst, r)
            if ok and H <= inst.Tmax:
                assert evaluate(inst, PARAMS, r).objective >= sol.objective - 1e-9


def test_timing_bate_com_evaluate():
    inst = random_instance(1)
    route = greedy.solve(inst, PARAMS).route
    ev = evaluate(inst, PARAMS, route)
    H, walk, ok = timing(inst, route)
    assert ok and H == pytest.approx(ev.H) and walk == pytest.approx(ev.walk)


def test_instancia_minima_dos_arquivos(tmp_path):
    _, pre = instance_from_files(write_mini_instance(tmp_path / "mini"))
    sol = greedy.solve(pre.instance, PARAMS)
    assert sol.feasible and sol.route[1] == 1  # a urgente (índice 1) vem primeiro
    # só fica de fora o domicílio de janela à tarde e penalidade 0,1 (ganho β·0,1 = 3 min): no mesmo ponto
    # da gestante ele atrasaria o idoso, cuja janela fecha em 180; nas outras posições custa 6 min a pé
    assert sol.route == [0, 1, 3, 2, 5, 4, 0]
    assert [(pre.ids()[i], m) for i, m in sol.unvisited] == [(5, "nao_coube")]
