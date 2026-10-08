"""
Construção gulosa (etapa 1 do algoritmo, §6.5 da proposta).

  1. urgências primeiro, em ordem de vizinho mais próximo a partir da UBS;
  2. para cada candidata fora da rota, a melhor posição de inserção depois do bloco de urgências (a que
     menos aumenta caminhada + γ·excesso; empate: menor horário de retorno H), respeitando janelas, Tmax
     e o teto de graves;
  3. insere a candidata de maior razão β·penalidade ÷ minutos acrescentados, desde que a inserção
     melhore o objetivo (caminhada + β·penalidade residual + γ·excesso);
  4. repete até nenhuma candidata caber.

As que sobram ficam com motivo `teto_graves` (grave barrada pelo teto) ou `nao_coube`.
"""

from time import perf_counter

from .evaluation import build_solution, timing
from .instance import Instance, Params, Solution


def urgent_route(inst: Instance) -> list[int]:
    """UBS → urgentes por vizinho mais próximo → UBS."""
    route, here, todo = [0], 0, sorted(inst.urgent)
    while todo:
        nxt = min(todo, key=lambda i: (inst.t[here, i], i))
        todo.remove(nxt)
        route.append(nxt)
        here = nxt
    return route + [0]


def graves_limit(inst: Instance, route: list[int]) -> int:
    """Teto efetivo de graves (decisão D6): urgentes graves são obrigatórias mesmo acima de K."""
    return max(inst.K, sum(inst.visits[i].urgent and inst.visits[i].grave for i in route))


def best_insertion(inst: Instance, params: Params, route: list[int], c: int,
                   first_pos: int) -> tuple[int, float, float] | None:
    """
    Posição de `c` (a partir de `first_pos`) que menos aumenta o custo da rota (caminhada + γ·excesso),
    sem violar janelas nem Tmax; empate pelo menor H. Devolve (posição, H, caminhada).
    """
    best, best_key = None, None
    for p in range(first_pos, len(route)):
        H, walk, ok = timing(inst, route[:p] + [c] + route[p:])
        if not ok or H > inst.Tmax + 1e-9:
            continue
        key = (walk + params.gamma * max(0.0, H - inst.T), H)
        if best_key is None or key < best_key:
            best, best_key = (p, H, walk), key
    return best


def solve(inst: Instance, params: Params) -> Solution:
    start = perf_counter()
    route = urgent_route(inst)
    first_pos = len(route) - 1  # inserções só depois do bloco de urgências
    limit = graves_limit(inst, route)
    graves = sum(inst.visits[i].grave for i in route)
    H, walk, _ = timing(inst, route)
    pending = sorted(i for i in inst.candidates if not inst.visits[i].urgent)

    def overtime(h):
        return max(0.0, h - inst.T)

    while pending:
        best = None  # (razão, candidata, posição, H, caminhada)
        for c in pending:
            v = inst.visits[c]
            if v.grave and graves >= limit:
                continue
            ins = best_insertion(inst, params, route, c, first_pos)
            if ins is None:
                continue
            p, H2, walk2 = ins
            gain = params.beta * v.penalty
            delta = (walk2 - walk) + params.gamma * (overtime(H2) - overtime(H)) - gain
            if delta >= 0:  # inserir pioraria o objetivo
                continue
            ratio = gain / max(H2 - H, 1e-9)
            if best is None or ratio > best[0]:
                best = (ratio, c, p, H2, walk2)
        if best is None:
            break
        _, c, p, H, walk = best
        route.insert(p, c)
        pending.remove(c)
        graves += inst.visits[c].grave

    return build_solution(inst, params, route, "guloso", runtime_s=perf_counter() - start,
                          unvisited_reasons=unvisited_reasons(inst, route))


def unvisited_reasons(inst: Instance, route: list[int]) -> dict[int, str]:
    """Motivo das candidatas fora da rota: `teto_graves` se é grave e o teto já foi atingido, senão `nao_coube`."""
    in_route = set(route)
    full = sum(inst.visits[i].grave for i in route) >= graves_limit(inst, route)
    return {c: "teto_graves" if inst.visits[c].grave and full else "nao_coube"
            for c in inst.candidates if c not in in_route}
