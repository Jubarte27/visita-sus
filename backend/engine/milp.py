"""
Referência exata (etapa 3 do algoritmo, §6.4 da proposta): o problema do dia como programa linear inteiro
misto, resolvido pelo HiGHS (highspy). Mede o gap da ALNS em instâncias pequenas; em instâncias maiores, para
no tempo limite com a melhor solução achada e o gap provado até ali.

Variáveis: y_i (visita i é feita), x_ij (vai de i direto para j; 0 = saída da UBS, e = chegada à UBS),
a_i (início do atendimento em i), H (retorno à UBS), E ≥ H − T (excesso).

    min  Σ t_ij x_ij + β Σ_i w_i (d_i+1)/P_i (1 − y_i) + γ E
    s.a. Σ_j x_0j = 1,  Σ_i x_ie = 1,  Σ_j x_ij = Σ_j x_ji = y_i
         a_j ≥ a_i + s_i + t_ij − M (1 − x_ij)        (tempo; também elimina subciclos, pois s_i > 0)
         a_j ≥ t_0j − M (1 − x_0j),  H ≥ a_i + s_i + t_ie − M (1 − x_ie)
         tw_a_i ≤ a_i ≤ tw_b_i + M (1 − y_i),  H ≤ Tmax
         y_i = 1 (i urgente);  a_j ≥ a_i + s_i − M (1 − y_j)  (i urgente, j não urgente)
         Σ_{i grave} y_i ≤ max(K, nº de urgentes graves)  (decisão D6)

O solver parte de uma solução inicial (a rota gulosa, ou `initial`), então nunca devolve nada pior que ela.
Os a_i do modelo podem ficar acima do cronograma mais cedo; a rota extraída é reavaliada por
evaluation.evaluate. O gap é o do solver: (incumbente − limitante) / incumbente, 0 = ótimo provado.
"""

from time import perf_counter

import highspy

from . import greedy
from .evaluation import build_solution, schedule
from .instance import Instance, Params, Solution

TEMPO_PADRAO_S = 60.0
GAP_REL = 1e-6  # tolerância de otimalidade (o padrão do HiGHS, 1e-4, é frouxo para uma referência)
FIM = "e"       # nó de chegada à UBS


class Modelo:
    """Modelo HiGHS do dia de um ACS, com as variáveis indexadas para a solução inicial e a leitura da rota."""

    def __init__(self, inst: Instance, params: Params):
        self.inst = inst
        V = list(inst.candidates)
        vis, t = inst.visits, inst.t
        ok = lambda i, j: t[i, j] < float("inf")
        self.tt = lambda i, j: float(t[i, 0 if j == FIM else j])
        M = inst.Tmax + max((vis[i].s for i in V), default=0) + float(
            max((t[i, j] for i in [0, *V] for j in [0, *V] if ok(i, j)), default=0))

        h = self.h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        self.y = {i: h.addBinary(name=f"y_{i}") for i in V}
        self.a = {i: h.addVariable(lb=vis[i].tw[0], ub=inst.Tmax, name=f"a_{i}") for i in V}
        self.H = h.addVariable(lb=0, ub=inst.Tmax, name="H")
        self.E = h.addVariable(lb=0, ub=highspy.kHighsInf, name="E")
        arcs = [(0, j) for j in V if ok(0, j)] + [(i, j) for i in V for j in V if i != j and ok(i, j)]
        arcs += [(i, FIM) for i in V if ok(i, 0)] + [(0, FIM)]
        self.x = {(i, j): h.addBinary(name=f"x_{i}_{j}") for i, j in arcs}
        x, y, a, H, E = self.x, self.y, self.a, self.H, self.E

        h.addConstr(sum(x[0, j] for j in [*V, FIM] if (0, j) in x) == 1)
        h.addConstr(sum(x[i, FIM] for i in [0, *V] if (i, FIM) in x) == 1)
        for i in V:
            h.addConstr(sum(x[i, j] for j in [*V, FIM] if (i, j) in x) - y[i] == 0)
            h.addConstr(sum(x[j, i] for j in [0, *V] if (j, i) in x) - y[i] == 0)
            h.addConstr(a[i] + M * y[i] <= vis[i].tw[1] + M)
        for i, j in arcs:
            if i == 0 and j != FIM:
                h.addConstr(a[j] - M * x[i, j] >= self.tt(0, j) - M)
            elif i != 0 and j == FIM:
                h.addConstr(H - a[i] - M * x[i, j] >= vis[i].s + self.tt(i, FIM) - M)
            elif i != 0:
                h.addConstr(a[j] - a[i] - M * x[i, j] >= vis[i].s + self.tt(i, j) - M)
        h.addConstr(E - H >= -inst.T)

        urgent = [i for i in V if vis[i].urgent]
        for i in urgent:
            h.addConstr(y[i] == 1)
            for j in V:
                if not vis[j].urgent:
                    h.addConstr(a[j] - a[i] - M * y[j] >= vis[i].s - M)
        graves = [i for i in V if vis[i].grave]
        if graves:
            h.addConstr(sum(y[i] for i in graves) <= max(inst.K, sum(vis[i].urgent for i in graves)))

        pen = sum(vis[i].penalty for i in V)  # constante: β Σ pen (1 − y) = β Σ pen − β Σ pen·y
        self.objetivo = (sum(self.tt(i, j) * x[i, j] for i, j in arcs)
                         - params.beta * sum(vis[i].penalty * y[i] for i in V) + params.gamma * E)
        self.constante = params.beta * pen

    def iniciar_com(self, route: list[int]) -> None:
        """Solução inicial a partir de uma rota viável (cronograma mais cedo)."""
        valores = [0.0] * self.h.getNumCol()
        stops, H, _ = schedule(self.inst, route)
        for i, a in self.a.items():
            valores[a.index] = self.inst.visits[i].tw[0]
        for st in stops:
            valores[self.y[st.visit].index] = 1.0
            valores[self.a[st.visit].index] = st.start
        nos = [0, *route[1:-1], FIM]
        for i, j in zip(nos, nos[1:]):
            valores[self.x[i, j].index] = 1.0
        valores[self.H.index] = H
        valores[self.E.index] = max(0.0, H - self.inst.T)
        sol = highspy.HighsSolution()
        sol.col_value = valores
        sol.value_valid = True
        self.h.setSolution(sol)

    def rota(self) -> list[int]:
        valores = self.h.getSolution().col_value
        route, here = [0], 0
        while True:
            nxt = next((j for (i, j), v in self.x.items() if i == here and valores[v.index] > 0.5), None)
            if nxt is None or nxt == FIM:
                return route + [0]
            route.append(nxt)
            here = nxt
            if len(route) > self.inst.n + 1:
                raise RuntimeError("rota do MILP não fecha (ciclo)")


def solve(inst: Instance, params: Params, time_limit_s: float | None = None, initial: list[int] | None = None,
          msg: bool = False) -> Solution:
    start = perf_counter()
    m = Modelo(inst, params)
    m.h.setOptionValue("output_flag", msg)
    m.h.setOptionValue("time_limit", float(time_limit_s or TEMPO_PADRAO_S))
    m.h.setOptionValue("mip_rel_gap", GAP_REL)
    # objetivo antes da solução inicial: minimize(expr) redefine o objetivo e descartaria a solução já passada
    m.h.setObjective(m.objetivo, highspy.ObjSense.kMinimize)
    m.h.changeObjectiveOffset(m.constante)  # β Σ penalidades: o gap do solver fica relativo ao objetivo verdadeiro
    m.iniciar_com(initial or greedy.solve(inst, params).route)
    m.h.run()
    info = m.h.getInfo()
    tem_solucao = info.primal_solution_status == 2  # kSolutionStatusFeasible
    route = m.rota() if tem_solucao else (initial or greedy.solve(inst, params).route)
    gap = float(info.mip_gap) if tem_solucao and info.mip_gap < highspy.kHighsInf else None
    return build_solution(inst, params, route, "milp", runtime_s=perf_counter() - start, gap=gap,
                          unvisited_reasons=greedy.unvisited_reasons(inst, route))
