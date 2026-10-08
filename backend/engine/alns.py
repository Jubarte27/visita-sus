"""
ALNS: Busca Adaptativa em Grandes Vizinhanças (etapa 2 do algoritmo, §6.5 da proposta).

Parte da construção gulosa e repete, até `iterations` ou `time_limit_s`:
  1. destruição: tira de 10% a 40% das visitas não urgentes (aleatória, pior custo, geográfica/Shaw,
     segmento contíguo, arestas caras);
  2. reparo: reinsere visitas, removidas ou que já estavam fora (inserção gulosa, regret-2, maior
     penalidade primeiro, inserção mais barata, agrupada); só insere quando melhora o objetivo, sempre
     respeitando janelas, Tmax e o teto de graves;
  3. busca local dentro de cada bloco (urgências / demais): 2-opt e or-opt (mover um trecho de 1 a 3 visitas
     para outra posição do bloco), e sanitização (urgências no início);
  4. aceitação por Simulated Annealing: pior por Δ é aceita com probabilidade exp(−Δ/τ), τ decrescente;
  5. adaptação: operadores ganham pontos por nova melhor (33), melhora (9) ou aceitação (13); a cada
     segmento de 25 iterações, os pesos da roleta são atualizados.

O objetivo é o de evaluation.py (minimizar caminhada + β·penalidade residual + γ·excesso). As urgências
ficam fixas no início (construídas pelo guloso); os operadores só mexem no bloco das não urgentes.

Inserções são avaliadas em O(1) com o esquema de folgas de Savelsbergh (RouteState); a rota escolhida
é sempre conferida pelo cronograma completo (`timing`).
"""

import math
import random
import statistics
from dataclasses import dataclass
from time import perf_counter

from . import greedy
from .evaluation import build_solution, timing
from .instance import Instance, Params, Solution

INF = float("inf")
SEGMENT = 25                      # iterações entre atualizações dos pesos
REACTION = 0.2                    # inércia da atualização dos pesos
MIN_WEIGHT = 0.05
R_BEST, R_BETTER, R_ACCEPTED = 33.0, 9.0, 13.0


class RouteState:
    """
    Cronograma de uma rota com as folgas que permitem avaliar inserções em O(1).

    Para cada posição k (0 = UBS de saída, m+1 = UBS de chegada): chegada A, início S, espera W = S − A,
    saída D = S + s, soma das esperas de k até o fim SW e folga MS (quanto o início em k pode atrasar sem
    violar janelas adiante nem Tmax).
    """

    def __init__(self, inst: Instance, route: list[int]):
        self.inst, self.route = inst, route
        t, vis = inst.t, inst.visits
        n = len(route)
        A, S, W, D = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n
        for k in range(1, n):
            i = route[k]
            A[k] = D[k - 1] + t[route[k - 1], i]
            a = vis[i].tw[0] if k < n - 1 else 0.0
            S[k] = max(A[k], a)
            W[k] = S[k] - A[k]
            D[k] = S[k] + (vis[i].s if k < n - 1 else 0.0)
        self.A, self.S, self.W, self.D = A, S, W, D
        self.H = A[-1]
        SW, MS = [0.0] * n, [0.0] * n
        MS[-1] = inst.Tmax - self.H
        for k in range(n - 2, 0, -1):
            SW[k] = SW[k + 1] + W[k]
            MS[k] = min(vis[route[k]].tw[1] - S[k], W[k + 1] + MS[k + 1])
        self.SW, self.MS = SW, MS
        self.walk = sum(t[route[k - 1], route[k]] for k in range(1, n))

    def insertion(self, c: int, p: int) -> tuple[float, float] | None:
        """Inserir `c` antes da posição p (1..m+1): (Δcaminhada, ΔH) ou None se violar janela/Tmax."""
        t, v = self.inst.t, self.inst.visits[c]
        prev, nxt = self.route[p - 1], self.route[p]
        start = self.D[p - 1] + t[prev, c]
        if start < v.tw[0]:
            start = v.tw[0]
        elif start > v.tw[1] + 1e-9:
            return None
        delta = start + v.s + t[c, nxt] - self.A[p]
        if delta > self.W[p] + self.MS[p] + 1e-9:
            return None
        return t[prev, c] + t[c, nxt] - t[prev, nxt], max(0.0, delta - self.SW[p])


@dataclass
class _Move:
    candidate: int
    position: int
    cost: float     # Δ(caminhada + γ·excesso)
    dH: float


class ALNS:
    def __init__(self, inst: Instance, params: Params, seed: int):
        self.inst, self.params = inst, params
        self.rng = random.Random(seed)
        self.seed = seed
        vis = inst.visits
        self.pen = [v.penalty for v in vis]
        self.total_pen = sum(self.pen[c] for c in inst.candidates)
        urgent = greedy.urgent_route(inst)
        self.first = len(urgent) - 1          # primeira posição do bloco não urgente
        self.limit = greedy.graves_limit(inst, urgent)
        self.regular = [c for c in inst.candidates if not vis[c].urgent]
        self.destroy_ops = [self.destroy_random, self.destroy_worst, self.destroy_shaw,
                            self.destroy_segment, self.destroy_expensive]
        self.repair_ops = [self.repair_greedy, self.repair_regret, self.repair_by_penalty,
                           self.repair_cheapest, self.repair_cluster]

    # ---------- avaliação ----------
    def objective(self, route: list[int]) -> float:
        """Objetivo da rota, ou inf se violar janela, Tmax ou o teto de graves."""
        H, walk, ok = timing(self.inst, route)
        if not ok or H > self.inst.Tmax + 1e-9:
            return INF
        vis = self.inst.visits
        if sum(vis[i].grave for i in route) > self.limit:
            return INF
        residual = self.total_pen - sum(self.pen[i] for i in route[1:-1])
        p = self.params
        return walk + p.beta * residual + p.gamma * max(0.0, H - self.inst.T)

    def _cost(self, state: RouteState, dwalk: float, dH: float) -> float:
        T, g = self.inst.T, self.params.gamma
        return dwalk + g * (max(0.0, state.H + dH - T) - max(0.0, state.H - T))

    def _moves(self, state: RouteState, c: int) -> list[_Move]:
        """Inserções viáveis de `c` no bloco não urgente, da mais barata para a mais cara."""
        moves = []
        for p in range(self.first, len(state.route)):
            ins = state.insertion(c, p)
            if ins is not None:
                moves.append(_Move(c, p, self._cost(state, *ins), ins[1]))
        moves.sort(key=lambda m: (m.cost, m.dH))
        return moves

    def _pending(self, route: list[int], pool) -> list[int]:
        """Candidatas de `pool` fora da rota que ainda podem entrar (teto de graves)."""
        in_route = set(route)
        full = sum(self.inst.visits[i].grave for i in route) >= self.limit
        return [c for c in pool if c not in in_route and not (full and self.inst.visits[c].grave)]

    def _gain(self, c: int) -> float:
        return self.params.beta * self.pen[c]

    def _insert(self, route: list[int], m: _Move) -> list[int]:
        return route[:m.position] + [m.candidate] + route[m.position:]

    # ---------- destruição ----------
    def _regular_positions(self, route):
        return list(range(self.first, len(route) - 1))

    def _remove(self, route, positions):
        drop = set(positions)
        return [x for k, x in enumerate(route) if k not in drop]

    def destroy_random(self, route, q):
        pos = self._regular_positions(route)
        return self._remove(route, self.rng.sample(pos, min(q, len(pos))))

    def destroy_worst(self, route, q):
        """Tira as visitas cuja retirada mais melhora o objetivo (com ruído, para variar)."""
        base = self.objective(route)
        scored = []
        for k in self._regular_positions(route):
            delta = self.objective(route[:k] + route[k + 1:]) - base
            scored.append((delta * self.rng.uniform(0.8, 1.2) if delta > 0 else delta, k))
        scored.sort()
        return self._remove(route, [k for _, k in scored[:q]])

    def destroy_shaw(self, route, q):
        """Tira uma visita sorteada e as mais próximas dela a pé."""
        pos = self._regular_positions(route)
        if not pos:
            return route
        seed = route[self.rng.choice(pos)]
        t = self.inst.t
        pos.sort(key=lambda k: t[seed, route[k]] + t[route[k], seed])
        return self._remove(route, pos[:q])

    def destroy_segment(self, route, q):
        pos = self._regular_positions(route)
        if not pos:
            return route
        q = min(q, len(pos))
        start = self.rng.randint(0, len(pos) - q)
        return self._remove(route, pos[start:start + q])

    def destroy_expensive(self, route, q):
        """Tira as visitas com maior desvio de caminhada mais duração."""
        t, vis = self.inst.t, self.inst.visits
        scored = []
        for k in self._regular_positions(route):
            a, i, b = route[k - 1], route[k], route[k + 1]
            scored.append((t[a, i] + t[i, b] - t[a, b] + vis[i].s, k))
        scored.sort(reverse=True)
        return self._remove(route, [k for _, k in scored[:q]])

    # ---------- reparo (só insere com ganho no objetivo) ----------
    def _best_move(self, state, c):
        moves = self._moves(state, c)
        if moves and moves[0].cost < self._gain(c):
            return moves[0]
        return None

    def repair_greedy(self, route):
        """Maior razão penalidade evitada ÷ minutos acrescentados (critério da construção gulosa)."""
        while True:
            state, best, best_ratio = RouteState(self.inst, route), None, -INF
            for c in self._pending(route, self.regular):
                m = self._best_move(state, c)
                if m is not None:
                    ratio = self._gain(c) / max(m.dH, 1e-9)
                    if ratio > best_ratio:
                        best, best_ratio = m, ratio
            if best is None:
                return route
            route = self._insert(route, best)

    def repair_regret(self, route):
        """Regret-2: primeiro quem mais perde se não entrar agora na melhor posição."""
        while True:
            state, best, best_regret = RouteState(self.inst, route), None, -INF
            for c in self._pending(route, self.regular):
                moves = self._moves(state, c)
                if not moves or moves[0].cost >= self._gain(c):
                    continue
                second = moves[1].cost if len(moves) > 1 else self._gain(c)
                regret = min(second, self._gain(c)) - moves[0].cost
                if regret > best_regret:
                    best, best_regret = moves[0], regret
            if best is None:
                return route
            route = self._insert(route, best)

    def repair_by_penalty(self, route):
        """Maior penalidade primeiro, cada uma na sua posição mais barata."""
        for c in sorted(self._pending(route, self.regular), key=lambda c: -self.pen[c]):
            if c in self._pending(route, [c]):
                m = self._best_move(RouteState(self.inst, route), c)
                if m is not None:
                    route = self._insert(route, m)
        return route

    def repair_cheapest(self, route):
        """Maior ganho líquido (β·penalidade − custo da inserção) primeiro."""
        while True:
            state, best, best_net = RouteState(self.inst, route), None, 0.0
            for c in self._pending(route, self.regular):
                m = self._best_move(state, c)
                if m is not None and self._gain(c) - m.cost > best_net:
                    best, best_net = m, self._gain(c) - m.cost
            if best is None:
                return route
            route = self._insert(route, best)

    def repair_cluster(self, route):
        """Insere uma visita e tenta encaixar as vizinhas dela ao lado; completa com a gulosa."""
        pending = self._pending(route, self.regular)
        if not pending:
            return route
        state = RouteState(self.inst, route)
        options = [m for m in (self._best_move(state, c) for c in pending) if m is not None]
        if not options:
            return route
        seed = max(options, key=lambda m: self._gain(m.candidate) / max(m.dH, 1e-9))
        route = self._insert(route, seed)
        t, s = self.inst.t, seed.candidate
        for c in sorted(self._pending(route, self.regular), key=lambda c: t[s, c] + t[c, s]):
            if c not in self._pending(route, [c]):
                continue
            k = route.index(s)
            state = RouteState(self.inst, route)
            moves = [m for m in self._moves(state, c) if m.position in (k, k + 1)]
            if moves and moves[0].cost < self._gain(c):
                route = self._insert(route, moves[0])
        return self.repair_greedy(route)

    # ---------- busca local e sanitização ----------
    def two_opt(self, route: list[int]) -> list[int]:
        """2-opt de primeira melhora, invertendo trechos dentro de um mesmo bloco (urgências ou demais)."""
        t = self.inst.t
        best = self.objective(route)
        blocks = [(1, self.first - 1), (self.first, len(route) - 2)]
        improved = True
        while improved:
            improved = False
            blocks[1] = (self.first, len(route) - 2)
            for lo, hi in blocks:
                for i in range(lo, hi):
                    for j in range(i + 1, hi + 1):
                        a, b, c, d = route[i - 1], route[i], route[j], route[j + 1]
                        if t[a, c] + t[b, d] - t[a, b] - t[c, d] >= -1e-9:
                            continue
                        cand = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                        obj = self.objective(cand)
                        if obj < best - 1e-9:
                            route, best, improved = cand, obj, True
                            break
                    if improved:
                        break
                if improved:
                    break
        return route

    def or_opt(self, route: list[int]) -> list[int]:
        """
        Or-opt de primeira melhora: move um trecho de 1 a 3 visitas para outra posição do mesmo bloco. Só avalia
        o objetivo completo quando o movimento encurta a caminhada (teste em O(1)).
        """
        t = self.inst.t
        best = self.objective(route)
        improved = True
        while improved:
            improved = False
            for lo, hi in ((1, self.first - 1), (self.first, len(route) - 2)):
                for k in (1, 2, 3):
                    for i in range(lo, hi - k + 2):
                        j = i + k - 1  # trecho route[i..j]
                        a, b = route[i - 1], route[j + 1]
                        s0, s1 = route[i], route[j]
                        removido = t[a, s0] + t[s1, b] - t[a, b]
                        for p in range(lo - 1, hi + 1):  # inserir entre route[p] e route[p + 1]
                            if i - 1 <= p <= j:
                                continue
                            c, d = route[p], route[p + 1]
                            if t[c, s0] + t[s1, d] - t[c, d] - removido >= -1e-9:
                                continue
                            seg = route[i:j + 1]
                            resto = route[:i] + route[j + 1:]
                            q = p + 1 if p < i else p + 1 - k
                            cand = resto[:q] + seg + resto[q:]
                            obj = self.objective(cand)
                            if obj < best - 1e-9:
                                route, best, improved = cand, obj, True
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
        return route

    def busca_local(self, route: list[int]) -> list[int]:
        """2-opt e or-opt alternados até nenhum dos dois melhorar."""
        while True:
            obj = self.objective(route)
            route = self.or_opt(self.two_opt(route))
            if self.objective(route) >= obj - 1e-9:
                return route

    def sanitize(self, route: list[int]) -> list[int]:
        """Urgências no início (na ordem em que aparecem), as demais depois."""
        vis = self.inst.visits
        inner = route[1:-1]
        return [0] + [i for i in inner if vis[i].urgent] + [i for i in inner if not vis[i].urgent] + [0]

    # ---------- laço principal ----------
    def run(self, initial: list[int]) -> tuple[list[int], float, int]:
        p, rng = self.params, self.rng
        deadline = perf_counter() + p.time_limit_s
        current = self.sanitize(self.busca_local(list(initial)))
        cur_obj = self.objective(current)
        best, best_obj = list(current), cur_obj
        dw, rw = [1.0] * len(self.destroy_ops), [1.0] * len(self.repair_ops)
        ds, dc = [0.0] * len(dw), [0] * len(dw)
        rs, rc = [0.0] * len(rw), [0] * len(rw)
        tau = p.t_start
        it = 0
        while it < p.iterations and perf_counter() < deadline:
            it += 1
            di = rng.choices(range(len(dw)), weights=dw)[0]
            ri = rng.choices(range(len(rw)), weights=rw)[0]
            n_reg = len(current) - 1 - self.first
            q = max(1, round(n_reg * rng.uniform(p.destroy_min, p.destroy_max))) if n_reg else 0
            cand = self.destroy_ops[di](current, q) if q else current
            cand = self.sanitize(self.busca_local(self.repair_ops[ri](cand)))
            obj = self.objective(cand)

            reward = 0.0
            if obj < best_obj - 1e-9:
                best, best_obj, current, cur_obj, reward = list(cand), obj, cand, obj, R_BEST
            elif obj < cur_obj - 1e-9:
                current, cur_obj, reward = cand, obj, R_BETTER
            elif obj < INF and rng.random() < math.exp(-(obj - cur_obj) / max(tau, 1e-9)):
                current, cur_obj, reward = cand, obj, R_ACCEPTED
            ds[di] += reward; dc[di] += 1
            rs[ri] += reward; rc[ri] += 1

            if it % SEGMENT == 0:
                for w, sc, cn in ((dw, ds, dc), (rw, rs, rc)):
                    for k in range(len(w)):
                        if cn[k]:
                            w[k] = max(MIN_WEIGHT, (1 - REACTION) * w[k] + REACTION * sc[k] / cn[k])
                        sc[k], cn[k] = 0.0, 0
            tau *= p.cooling
        return best, best_obj, it


def solve(inst: Instance, params: Params, initial: list[int] | None = None, seed: int = 0) -> Solution:
    """ALNS com uma semente, partindo de `initial` (padrão: a construção gulosa)."""
    start = perf_counter()
    if initial is None:
        initial = greedy.solve(inst, params).route
    route, _, _ = ALNS(inst, params, seed).run(initial)
    return build_solution(inst, params, route, "alns", seed=seed, runtime_s=perf_counter() - start,
                          unvisited_reasons=greedy.unvisited_reasons(inst, route))


def solve_multi_seed(inst: Instance, params: Params) -> Solution:
    """Roda as sementes de `params.seeds` a partir do mesmo guloso; devolve a melhor com a variação entre elas."""
    start = perf_counter()
    initial = greedy.solve(inst, params).route
    runs = [solve(inst, params, initial, seed) for seed in params.seeds]
    best = min(runs, key=lambda s: (not s.feasible, s.objective))
    objs = [s.objective for s in runs]
    best.seeds_stats = {
        "sementes": list(params.seeds), "objetivos": objs,
        "media": statistics.fmean(objs), "desvio": statistics.pstdev(objs),
        "melhor": min(objs), "pior": max(objs),
        "tempos_s": [s.runtime_s for s in runs],
    }
    best.runtime_s = perf_counter() - start
    return best
