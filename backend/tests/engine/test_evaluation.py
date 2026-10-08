"""
Avaliação de rotas sobre uma instância de 5 pontos com valores conferidos à mão.

Tempos a pé (simétricos, min):      Visitas (s, w, P, d → penalidade = w·(d+1)/P):
      0   1   2   3   4             1: s=10 w=2 P=30 d=29 → 2.0  rotina
  0   0   5  10   8  12             2: s=20 w=5 P=7  d=6  → 5.0  urgente, grave
  1   5   0   4   7   9             3: s=15 w=1 P=60 d=65 → 1.1  atrasado, janela [40, 50]
  2  10   4   0   6   3             4: s=30 w=4 P=15 d=2  → 0.8  grave (risco)
  3   8   7   6   0   5
  4  12   9   3   5   0             T=60, Tmax=90, K=1, β=30, γ=2
"""

import subprocess
import sys
from pathlib import Path

import pytest

from engine.evaluation import build_solution, evaluate, is_feasible, schedule
from engine.instance import Instance, Params, Visit

BACKEND = Path(__file__).resolve().parents[2]
PARAMS = Params(beta=30, gamma=2)


def kinds(ev):
    return sorted((v.kind, v.visit) for v in ev.violations)


def test_penalidades(inst):
    assert [v.penalty for v in inst.visits] == pytest.approx([0, 2.0, 5.0, 1.1, 0.8])


def test_rota_viavel_sem_espera(inst):
    # 0 →(10) 2 [10–30] →(4) 1 [34–44] →(5) 0: H=49, caminhada 19, fora 3 e 4 (1.1 + 0.8)
    ev = evaluate(inst, PARAMS, [0, 2, 1, 0])
    assert [(s.visit, s.arrival, s.start, s.end) for s in ev.stops] == [(2, 10, 10, 30), (1, 34, 34, 44)]
    assert (ev.H, ev.walk, ev.overtime) == (49, 19, 0)
    assert ev.residual_penalty == pytest.approx(1.9)
    assert ev.objective == pytest.approx(19 + 30 * 1.9)  # 76
    assert ev.feasible


def test_espera_pela_janela_e_excesso(inst):
    # 0 →(10) 2 [10–30] →(6) 3 chega 36, espera até 40 [40–55] →(7) 1 [62–72] →(5) 0: H=77
    ev = evaluate(inst, PARAMS, [0, 2, 3, 1, 0])
    assert [(s.visit, s.arrival, s.start, s.end) for s in ev.stops] == [(2, 10, 10, 30), (3, 36, 40, 55), (1, 62, 62, 72)]
    assert (ev.H, ev.walk, ev.overtime) == (77, 28, 17)
    assert ev.residual_penalty == pytest.approx(0.8)
    assert ev.objective == pytest.approx(28 + 30 * 0.8 + 2 * 17)  # 86
    assert ev.feasible


def test_violacao_de_janela_e_jornada(inst):
    # 0 →(10) 2 [10–30] →(4) 1 [34–44] →(7) 3 chega 51 > b=50 [51–66] →(8) 0: H=74
    ev = evaluate(inst, PARAMS, [0, 2, 1, 3, 0])
    assert kinds(ev) == [("janela", 3)]
    assert ev.violations[0].amount == pytest.approx(1)

    # 0 →(10) 2 [10–30] →(3) 4 [33–63] →(9) 1 [72–82] →(5) 0: H=87 ≤ 90; com 3 no fim, passa de Tmax
    ev = evaluate(inst, PARAMS, [0, 2, 4, 1, 0])
    assert ev.H == 87 and ("jornada", None) not in kinds(ev)
    inst.Tmax = 80
    ev = evaluate(inst, PARAMS, [0, 2, 4, 1, 0])
    assert ("jornada", None) in kinds(ev)
    assert next(v.amount for v in ev.violations if v.kind == "jornada") == pytest.approx(7)


def test_teto_graves(inst):
    # 2 (urgente grave) + 4 (grave) = 2 graves > max(K=1, 1 urgente grave)
    ev = evaluate(inst, PARAMS, [0, 2, 4, 0])
    assert kinds(ev) == [("teto_graves", None)]
    assert ev.violations[0].amount == 1


def test_urgente_grave_nao_e_barrado_pelo_teto(inst):
    # decisão D6: urgentes graves são obrigatórias mesmo com K=0
    inst.K = 0
    assert is_feasible(inst, [0, 2, 1, 0])
    assert not is_feasible(inst, [0, 2, 4, 0])


def test_urgente_ausente_e_fora_de_ordem(inst):
    assert kinds(evaluate(inst, PARAMS, [0, 1, 0])) == [("urgente_ausente", 2)]
    assert kinds(evaluate(inst, PARAMS, [0, 1, 2, 0])) == [("urgencia_fora_de_ordem", 2)]


def test_rota_vazia(inst):
    ev = evaluate(inst, PARAMS, [0, 0])
    assert (ev.H, ev.walk, ev.stops) == (0, 0, [])
    assert ev.residual_penalty == pytest.approx(8.9)
    assert kinds(ev) == [("urgente_ausente", 2)]


@pytest.mark.parametrize("route", [[1, 0], [0, 1], [0], [0, 1, 1, 0], [0, 5, 0], [0, 1, 0, 2, 0]])
def test_rota_mal_formada(inst, route):
    with pytest.raises(ValueError):
        schedule(inst, route)


def test_build_solution(inst):
    sol = build_solution(inst, PARAMS, [0, 2, 3, 1, 4, 0], "guloso", seed=7, runtime_s=0.5,
                         unvisited_reasons={})
    assert [(s.visit, s.reason) for s in sol.stops] == [(2, "urgencia"), (3, "atraso"), (1, "rotina"), (4, "risco")]
    assert sol.unvisited == []

    sol = build_solution(inst, PARAMS, [0, 2, 1, 0], "alns", unvisited_reasons={4: "teto_graves"})
    assert sol.unvisited == [(3, "nao_coube"), (4, "teto_graves")]  # ordem decrescente de penalidade
    assert sol.objective == pytest.approx(76) and sol.feasible
    d = sol.to_dict()
    assert d["feasible"] is True and d["method"] == "alns" and d["stops"][0]["reason"] == "urgencia"


def test_instancia_invalida():
    ubs = Visit(id=-1, node=0, s=0, w=0, P=0, d=0, tw=(0, 420))
    with pytest.raises(ValueError):
        Instance(visits=[ubs], t=[[0, 1], [1, 0]])
    with pytest.raises(ValueError):
        Instance(visits=[ubs], t=[[0]], T=500, Tmax=420)


def test_engine_nao_importa_django():
    code = "import sys, engine.instance, engine.evaluation; print(any(m.split('.')[0] == 'django' for m in sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
