"""
Pré-processamento sobre uma matriz escrita à mão (nós 10..14, UBS no nó 10), T=80, Tmax=100, K=2.

  t[10→11]=5   t[10→12]=60   t[10→13]=20   t[10→14]=20   t[13↔14]=40   (simétrica; demais pares 10)
"""

from datetime import date, timedelta

import numpy as np
import pytest

from engine.instance import Params
from engine.preprocess import Agent, Household, preprocess

PLANO = date(2026, 10, 9)
NODES = np.array([10, 11, 12, 13, 14])


def matrix():
    t = np.full((5, 5), 10.0)
    np.fill_diagonal(t, 0)
    for a, b, v in [(10, 11, 5), (10, 12, 60), (10, 13, 20), (10, 14, 20), (13, 14, 40)]:
        i, j = a - 10, b - 10
        t[i, j] = t[j, i] = v
    return t


def house(id, node, d, w=2, P=30, s=10, tw=(0, 100), urgent=False, grave=False):
    return Household(id=id, node=node, s=s, w=w, P=P, ultima_visita=PLANO - timedelta(days=d), tw=tw,
                     urgent=urgent, grave=grave)


@pytest.fixture
def result():
    households = [
        house(1, 11, d=40),                          # penalidade 2·41/30 ≈ 2.73
        house(2, 11, d=20),                          # ≈ 1.40
        house(3, 11, d=5),                           # 0.40  → fica fora das 2 candidatas
        house(4, 12, d=50),                          # 60 + 10 + 60 > 100 → inviável
        house(5, 11, d=50, tw=(0, 3)),               # chega em 5, janela fecha em 3 → inviável
        house(6, 99, d=50),                          # nó fora da matriz → inviável
        house(7, 13, d=6, w=5, P=7, s=30, urgent=True, grave=True),   # penalidade 5
        house(8, 14, d=3, w=3, P=30, s=30, urgent=True),               # 0.4: juntas passam de Tmax
    ]
    agent = Agent(ubs_node=10, T=80, Tmax=100, K=2)
    return preprocess(households, agent, NODES, matrix(), PLANO, Params(n_candidatas=2))


def test_descartes_e_candidatas(result):
    assert sorted(result.discarded) == [(4, "inviavel"), (5, "inviavel"), (6, "inviavel"), (8, "urgencia_excedente")]
    assert result.not_candidates == [3]
    # UBS, urgentes, depois não urgentes por penalidade decrescente
    assert result.ids() == [-1, 7, 1, 2]


def test_instancia(result):
    inst = result.instance
    assert (inst.T, inst.Tmax, inst.K) == (80, 100, 2)
    assert inst.visits[0].node == 10 and inst.visits[0].tw == (0, 100)
    assert [v.d for v in inst.visits[1:]] == [6, 40, 20]
    assert inst.visits[2].penalty == pytest.approx(2 * 41 / 30)
    assert inst.urgent == [1]
    # nós 10, 13, 11, 11
    assert inst.t.tolist() == [[0, 20, 5, 5], [20, 0, 10, 10], [5, 10, 0, 0], [5, 10, 0, 0]]


def test_urgentes_que_cabem_juntas_ficam():
    agent = Agent(ubs_node=10, T=80, Tmax=200, K=2)
    hh = [house(7, 13, d=6, urgent=True), house(8, 14, d=3, urgent=True)]
    pre = preprocess(hh, agent, NODES, matrix(), PLANO)
    assert pre.discarded == [] and sorted(pre.ids()[1:]) == [7, 8]


def test_d_nao_fica_negativo():
    agent = Agent(ubs_node=10)
    h = house(1, 11, d=-3)  # última visita depois da data do plano
    pre = preprocess([h], agent, NODES, matrix(), PLANO)
    assert pre.instance.visits[1].d == 0


def test_ubs_fora_da_matriz():
    with pytest.raises(ValueError):
        preprocess([], Agent(ubs_node=999), NODES, matrix(), PLANO)
