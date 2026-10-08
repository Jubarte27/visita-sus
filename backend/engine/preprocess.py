"""
Pré-processamento do dia (módulo M3 da proposta): dos domicílios da microárea até a Instance do ACS.

  1. d = dias desde a última visita até a data do plano, e penalidade w·(d+1)/P;
  2. descarta visitas inviáveis sozinhas (sem caminho, ida + atendimento + volta além de Tmax, ou janela
     que fecha antes da chegada mais cedo possível): motivo `inviavel`;
  3. candidatas do dia: todas as urgentes + as `n_candidatas` não urgentes de maior penalidade;
  4. urgentes que não cabem juntas na jornada (rota de vizinho mais próximo a partir da UBS) saem, as de
     menor penalidade primeiro: motivo `urgencia_excedente`;
  5. monta a Instance: UBS no índice 0, depois urgentes e não urgentes em ordem decrescente de penalidade.

O resultado é usado igual pelo CLI (arquivos do gerador) e pelo backend (banco).
"""

from dataclasses import dataclass, field
from datetime import date

import numpy as np

from .instance import Instance, Params, Visit
from .matrix import submatrix


@dataclass
class Household:
    """Um domicílio da microárea, como vem do gerador ou do banco."""
    id: int
    node: int
    s: float
    w: float
    P: int
    ultima_visita: date
    tw: tuple[float, float]
    urgent: bool = False
    grave: bool = False


@dataclass
class Agent:
    ubs_node: int
    T: float = 360.0
    Tmax: float = 420.0
    K: int = 3


@dataclass
class Preprocessed:
    instance: Instance
    discarded: list[tuple[int, str]] = field(default_factory=list)  # (id do domicílio, motivo)
    not_candidates: list[int] = field(default_factory=list)         # ids viáveis que ficaram fora das candidatas

    def ids(self) -> list[int]:
        """id do domicílio de cada índice da Instance (índice 0 = UBS, id -1)."""
        return [v.id for v in self.instance.visits]


def to_visit(h: Household, plan_date: date) -> Visit:
    d = max(0, (plan_date - h.ultima_visita).days)
    return Visit(id=h.id, node=h.node, s=h.s, w=h.w, P=h.P, d=d, tw=h.tw, urgent=h.urgent, grave=h.grave)


def _alone_feasible(v: Visit, t_out: float, t_back: float, Tmax: float) -> bool:
    """A visita cabe sozinha na jornada: UBS → v → UBS respeitando a janela e Tmax."""
    if not (np.isfinite(t_out) and np.isfinite(t_back)):
        return False
    start = max(t_out, v.tw[0])
    return start <= v.tw[1] and start + v.s + t_back <= Tmax


def _urgent_route_end(urgent: list[Visit], time, ubs: int) -> float:
    """Retorno à UBS da rota de vizinho mais próximo só com as urgentes (inf se alguma janela fechar)."""
    clock, here, todo = 0.0, ubs, list(urgent)
    while todo:
        nxt = min(todo, key=lambda v: time(here, v.node))
        todo.remove(nxt)
        start = max(clock + time(here, nxt.node), nxt.tw[0])
        if start > nxt.tw[1]:
            return np.inf
        clock, here = start + nxt.s, nxt.node
    return clock + time(here, ubs)


def preprocess(households: list[Household], agent: Agent, nodes: np.ndarray, t: np.ndarray, plan_date: date,
               params: Params | None = None) -> Preprocessed:
    """
    `nodes`/`t` é a matriz de tempos da microárea (matrix.build_matrix), que deve conter o nó da UBS e
    os nós de todos os domicílios.
    """
    params = params or Params()
    pos = {int(n): i for i, n in enumerate(nodes)}
    if agent.ubs_node not in pos:
        raise ValueError(f"nó da UBS {agent.ubs_node} fora da matriz de tempos")

    def time(a, b):
        return float(t[pos[a], pos[b]])

    discarded, feasible = [], []
    for h in households:
        v = to_visit(h, plan_date)
        if h.node in pos and _alone_feasible(v, time(agent.ubs_node, h.node), time(h.node, agent.ubs_node), agent.Tmax):
            feasible.append(v)
        else:
            discarded.append((h.id, "inviavel"))

    by_penalty = lambda v: (-v.penalty, v.id)
    urgent = sorted((v for v in feasible if v.urgent), key=by_penalty)
    regular = sorted((v for v in feasible if not v.urgent), key=by_penalty)
    chosen, rest = regular[:params.n_candidatas], regular[params.n_candidatas:]

    # urgências que não cabem juntas: tira as de menor penalidade até a rota só de urgentes caber
    while urgent and _urgent_route_end(urgent, time, agent.ubs_node) > agent.Tmax:
        discarded.append((urgent.pop().id, "urgencia_excedente"))

    ubs_visit = Visit(id=-1, node=agent.ubs_node, s=0, w=0, P=0, d=0, tw=(0, agent.Tmax))
    visits = [ubs_visit] + urgent + chosen
    instance = Instance(visits=visits, t=submatrix(nodes, t, [v.node for v in visits]),
                        T=agent.T, Tmax=agent.Tmax, K=agent.K)
    return Preprocessed(instance=instance, discarded=discarded, not_candidates=[v.id for v in rest])

