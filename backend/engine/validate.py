"""
Validação experimental (§6.8 da proposta; métricas do Apêndice G de docs/passos-implementacao.md).

Para cada cenário (e cada microárea, numa instância de equipe):
  - instância completa: construção gulosa e ALNS com cada semente (uma linha por semente);
  - subinstâncias de --milp-n candidatas (--milp-reps sorteios): guloso, ALNS por semente e MILP, com o gap
    de cada heurística para o ótimo do MILP.
Roda em sequência, para os tempos de execução serem comparáveis. Uma linha do CSV por
(cenário, microárea, escopo, subinstância, método, semente).

    .venv/bin/python -m engine.validate --cenarios base=data/instances/bomjesus,... [--sementes 10 --milp-n 10]
"""

import argparse
import csv
import sys
from pathlib import Path

from . import alns, greedy, milp
from .instance import Params
from .io import instance_from_files, load_instance_files
from .subinstance import subinstance

RESULTADOS = Path(__file__).resolve().parent.parent / "data" / "resultados"
CENARIOS_PADRAO = ("base=data/instances/bomjesus,aglomerado=data/instances/val_aglomerado,"
                   "alta_urgencia=data/instances/val_urgencia,alto_atraso=data/instances/val_atraso,"
                   "equipe_4acs=data/instances/bomjesus_eq4")


def linha(cenario, microarea, escopo, sub, inst, discarded, metodo, semente, sol, ref=None) -> dict:
    """Métricas do Apêndice G para um plano."""
    vis = inst.visits
    fora = [i for i, _ in sol.unvisited]
    pos_urg = [k for k, st in enumerate(sol.stops, 1) if vis[st.visit].urgent]
    primeira_comum = next((k for k, st in enumerate(sol.stops, 1) if not vis[st.visit].urgent), len(sol.stops) + 1)
    return {
        "cenario": cenario, "microarea": microarea or "", "escopo": escopo, "sub": "" if sub is None else sub,
        "candidatas": inst.n - 1, "metodo": metodo, "semente": "" if semente is None else semente,
        "objetivo": round(sol.objective, 4), "caminhada_min": round(sol.walk, 3),
        "penalidade_residual": round(sol.residual_penalty, 4), "visitas": len(sol.stops),
        "urgentes": len(inst.urgent), "urgentes_atendidas": len(pos_urg),
        "urgencia_excedente": sum(m == "urgencia_excedente" for _, m in discarded),
        "ultima_posicao_urgencia": max(pos_urg, default=0), "urgencias_primeiro": max(pos_urg, default=0) < primeira_comum,
        "atrasados_candidatas": sum(vis[i].overdue for i in inst.candidates),
        "atrasados_fora": sum(vis[i].overdue for i in fora),
        "jornada_min": round(sol.H, 2), "excesso_min": round(sol.overtime, 2), "viavel": sol.feasible,
        "runtime_s": round(sol.runtime_s, 4),
        "gap_milp": "" if ref is None else round((sol.objective - ref) / abs(ref), 6) if ref else 0.0,
        "gap_solver": "" if sol.gap is None else round(sol.gap, 6),
    }


def validar_instancia(cenario, caminho, microarea, params, sementes, milp_n, milp_reps, tempo_milp):
    _, pre = instance_from_files(caminho, params=params, microarea=microarea)
    inst, desc = pre.instance, pre.discarded
    rows = []
    g = greedy.solve(inst, params)
    rows.append(linha(cenario, microarea, "completa", None, inst, desc, "guloso", None, g))
    for s in sementes:
        rows.append(linha(cenario, microarea, "completa", None, inst, desc, "alns", s,
                          alns.solve(inst, params, initial=g.route, seed=s)))
    for rep in range(milp_reps):
        sub = subinstance(inst, milp_n, seed=rep)
        m = milp.solve(sub, params, time_limit_s=tempo_milp)
        gs = greedy.solve(sub, params)
        rows.append(linha(cenario, microarea, "sub", rep, sub, [], "milp", None, m, m.objective))
        rows.append(linha(cenario, microarea, "sub", rep, sub, [], "guloso", None, gs, m.objective))
        for s in sementes:
            rows.append(linha(cenario, microarea, "sub", rep, sub, [], "alns", s,
                              alns.solve(sub, params, initial=gs.route, seed=s), m.objective))
    return rows


def main(argv=None):
    d = Params()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cenarios", default=CENARIOS_PADRAO, help="nome=pasta,... (padrão: os 5 cenários do P16)")
    ap.add_argument("--sementes", type=int, default=10, help="nº de sementes da ALNS (0..n-1)")
    ap.add_argument("--milp-n", type=int, default=10, help="candidatas por subinstância")
    ap.add_argument("--milp-reps", type=int, default=5, help="subinstâncias por cenário/microárea")
    ap.add_argument("--tempo-milp", type=float, default=60.0)
    ap.add_argument("--beta", type=float, default=d.beta)
    ap.add_argument("--gamma", type=float, default=d.gamma)
    ap.add_argument("--iteracoes", type=int, default=d.iterations)
    ap.add_argument("--saida", type=Path, default=RESULTADOS / "validacao.csv")
    args = ap.parse_args(argv)

    params = Params(beta=args.beta, gamma=args.gamma, iterations=args.iteracoes, time_limit_s=60.0)
    sementes = list(range(args.sementes))
    rows = []
    for item in args.cenarios.split(","):
        cenario, caminho = item.split("=", 1)
        mas = load_instance_files(caminho).microareas or [None]
        for ma in mas:
            print(f"{cenario}{f' · microárea {ma}' if ma else ''}…", end=" ", flush=True)
            novas = validar_instancia(cenario, caminho, ma, params, sementes, args.milp_n, args.milp_reps,
                                      args.tempo_milp)
            rows += novas
            comp = [r for r in novas if r["escopo"] == "completa"]
            ga = min(r["objetivo"] for r in comp if r["metodo"] == "alns")
            gg = next(r["objetivo"] for r in comp if r["metodo"] == "guloso")
            print(f"guloso {gg:.1f} · ALNS melhor {ga:.1f} ({100 * (ga - gg) / gg:+.2f}%)")
            sys.stdout.flush()
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} linhas gravadas em {args.saida}")


if __name__ == "__main__":
    main()
