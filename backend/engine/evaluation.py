"""
Avaliação de rotas: cronograma, função objetivo e viabilidade (§6.4 da proposta).

É a única implementação do objetivo; guloso, ALNS, MILP (para conferência) e testes usam estas funções.

    objetivo = caminhada + β · Σ_{candidatas fora da rota} w·(d+1)/P + γ · max(0, H − T)

Restrições verificadas (violações):
  janela                 início do atendimento depois do fim da janela (b)
  jornada                retorno à UBS depois de Tmax
  teto_graves            graves na rota acima de max(K, graves urgentes na rota) (decisão D6)
  urgente_ausente        urgente da instância fora da rota
  urgencia_fora_de_ordem urgente depois de alguma visita não urgente
"""

from dataclasses import dataclass, field

from .instance import W_RISCO, Instance, Params, Solution, Stop, Violation


@dataclass
class Evaluation:
    stops: list[Stop]
    H: float
    walk: float
    residual_penalty: float
    overtime: float
    objective: float
    violations: list[Violation] = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.violations


def validate_route(inst: Instance, route: list[int]) -> None:
    """Erros de construção da rota (não são violações do modelo): levanta ValueError."""
    if len(route) < 2 or route[0] != 0 or route[-1] != 0:
        raise ValueError(f"a rota deve começar e terminar na UBS (0): {route}")
    inner = route[1:-1]
    if any(not 0 < i < inst.n for i in inner):
        raise ValueError(f"índice fora das candidatas na rota: {route}")
    if len(set(inner)) != len(inner):
        raise ValueError(f"visita repetida na rota: {route}")


def schedule(inst: Instance, route: list[int]) -> tuple[list[Stop], float, float]:
    """
    Cronograma da rota a partir do instante 0 na UBS: em cada parada, chegada = fim anterior + caminhada,
    início = max(chegada, a) (espera a janela abrir), fim = início + s. Devolve (paradas, H, caminhada),
    em que H é o retorno à UBS (inclui esperas) e as paradas não incluem a UBS.
    """
    validate_route(inst, route)
    t, visits = inst.t, inst.visits
    stops, clock, walk = [], 0.0, 0.0
    for prev, i in zip(route[:-2], route[1:-1]):
        leg = float(t[prev, i])
        arrival = clock + leg
        start = max(arrival, visits[i].tw[0])
        clock = start + visits[i].s
        walk += leg
        stops.append(Stop(visit=i, arrival=arrival, start=start, end=clock, walk_from_prev=leg))
    back = float(t[route[-2], 0])
    return stops, clock + back, walk + back


def timing(inst: Instance, route: list[int]) -> tuple[float, float, bool]:
    """
    Versão rápida do cronograma para as heurísticas, sem validar a rota nem montar paradas:
    (H, caminhada, janelas respeitadas). Para na primeira janela violada (H = inf).
    """
    t, visits = inst.t, inst.visits
    clock = walk = 0.0
    prev = route[0]
    for i in route[1:-1]:
        leg = t[prev, i]
        a, b = visits[i].tw
        start = clock + leg
        if start < a:
            start = a
        elif start > b + 1e-9:
            return float("inf"), walk + leg, False
        clock = start + visits[i].s
        walk += leg
        prev = i
    back = t[prev, route[-1]]
    return float(clock + back), float(walk + back), True


def violations(inst: Instance, route: list[int], stops: list[Stop], H: float) -> list[Violation]:
    visits = inst.visits
    found = []
    for st in stops:
        b = visits[st.visit].tw[1]
        if st.start > b + 1e-9:
            found.append(Violation("janela", st.visit, st.start - b))
    if H > inst.Tmax + 1e-9:
        found.append(Violation("jornada", None, H - inst.Tmax))

    inner = route[1:-1]
    graves = [i for i in inner if visits[i].grave]
    limit = max(inst.K, sum(visits[i].urgent for i in graves))
    if len(graves) > limit:
        found.append(Violation("teto_graves", None, len(graves) - limit))

    in_route = set(inner)
    found += [Violation("urgente_ausente", i) for i in inst.urgent if i not in in_route]

    first_regular = next((pos for pos, i in enumerate(inner) if not visits[i].urgent), len(inner))
    found += [Violation("urgencia_fora_de_ordem", i) for i in inner[first_regular:] if visits[i].urgent]
    return found


def residual_penalty(inst: Instance, route: list[int]) -> float:
    """Soma das penalidades das candidatas que ficaram fora da rota."""
    in_route = set(route)
    return sum(inst.visits[i].penalty for i in inst.candidates if i not in in_route)


def evaluate(inst: Instance, params: Params, route: list[int]) -> Evaluation:
    stops, H, walk = schedule(inst, route)
    residual = residual_penalty(inst, route)
    overtime = max(0.0, H - inst.T)
    return Evaluation(
        stops=stops, H=H, walk=walk, residual_penalty=residual, overtime=overtime,
        objective=walk + params.beta * residual + params.gamma * overtime,
        violations=violations(inst, route, stops, H),
    )


def is_feasible(inst: Instance, route: list[int]) -> bool:
    stops, H, _ = schedule(inst, route)
    return not violations(inst, route, stops, H)


def visit_reason(inst: Instance, i: int) -> str:
    """Motivo de uma visita feita: urgência > atraso > risco clínico > rotina."""
    v = inst.visits[i]
    if v.urgent:
        return "urgencia"
    if v.overdue:
        return "atraso"
    if v.w >= W_RISCO:
        return "risco"
    return "rotina"


def build_solution(inst: Instance, params: Params, route: list[int], method: str, *, seed: int | None = None,
                   runtime_s: float = 0.0, unvisited_reasons: dict[int, str] | None = None,
                   seeds_stats: dict | None = None, gap: float | None = None) -> Solution:
    """
    Monta a Solution de uma rota. As candidatas fora da rota recebem o motivo de `unvisited_reasons`
    (padrão `nao_coube`), em ordem decrescente de penalidade.
    """
    ev = evaluate(inst, params, route)
    for st in ev.stops:
        st.reason = visit_reason(inst, st.visit)
    reasons = unvisited_reasons or {}
    in_route = set(route)
    out = sorted((i for i in inst.candidates if i not in in_route), key=lambda i: -inst.visits[i].penalty)
    return Solution(
        route=list(route), stops=ev.stops, unvisited=[(i, reasons.get(i, "nao_coube")) for i in out],
        walk=ev.walk, residual_penalty=ev.residual_penalty, overtime=ev.overtime, objective=ev.objective,
        H=ev.H, method=method, seed=seed, runtime_s=runtime_s, seeds_stats=seeds_stats, gap=gap,
        violations=ev.violations,
    )
