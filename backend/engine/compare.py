"""
Guloso × ALNS × MILP em subinstâncias de uma instância real (validação, §6.8 da proposta).

    .venv/bin/python -m engine.compare data/instances/bomjesus --n 10 --reps 5 [--microarea k] [--csv saida.csv]

Para cada repetição, sorteia n candidatas (semente = repetição), resolve com os três métodos e imprime o
objetivo, o tempo e o gap de cada heurística em relação ao MILP: (heurística − MILP) / MILP.
"""

import argparse
import csv
import statistics
import sys
from datetime import date
from pathlib import Path

from . import alns, greedy, milp
from .instance import Params
from .io import instance_from_files
from .subinstance import subinstance


def gap(h: float, ref: float) -> float:
    """Gap relativo da heurística para a referência; diferenças de arredondamento (< 1e-9) contam como 0."""
    g = (h - ref) / abs(ref) if ref else 0.0
    return 0.0 if abs(g) < 1e-9 else g


def compare(inst, params: Params, tempo_milp: float) -> dict:
    g = greedy.solve(inst, params)
    a = alns.solve_multi_seed(inst, params)
    m = milp.solve(inst, params, time_limit_s=tempo_milp)
    return {
        "guloso": g.objective, "alns": a.objective, "milp": m.objective,
        "milp_gap_solver": m.gap, "gap_guloso": gap(g.objective, m.objective), "gap_alns": gap(a.objective, m.objective),
        "t_guloso": g.runtime_s, "t_alns": a.runtime_s, "t_milp": m.runtime_s,
        "visitas_guloso": len(g.stops), "visitas_alns": len(a.stops), "visitas_milp": len(m.stops),
        "alns_desvio": (a.seeds_stats or {}).get("desvio"),
    }


def main():
    d = Params()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instancia", type=Path)
    ap.add_argument("--n", type=int, default=10, help="candidatas por subinstância (8 a 15)")
    ap.add_argument("--reps", type=int, default=5, help="nº de subinstâncias")
    ap.add_argument("--data", type=date.fromisoformat, default=None)
    ap.add_argument("--microarea", type=int, default=None)
    ap.add_argument("--beta", type=float, default=d.beta)
    ap.add_argument("--gamma", type=float, default=d.gamma)
    ap.add_argument("--sementes", default="0,1,2,3,4")
    ap.add_argument("--iteracoes", type=int, default=d.iterations)
    ap.add_argument("--tempo", type=float, default=2.0, help="tempo da ALNS por semente (s)")
    ap.add_argument("--tempo-milp", type=float, default=60.0)
    ap.add_argument("--csv", type=Path, default=None, help="grava uma linha por subinstância")
    args = ap.parse_args()

    params = Params(beta=args.beta, gamma=args.gamma, iterations=args.iteracoes, time_limit_s=args.tempo,
                    seeds=[int(s) for s in args.sementes.split(",")])
    files, pre = instance_from_files(args.instancia, args.data, params, args.microarea)
    print(f"{files.path.name}: {pre.instance.n - 1} candidatas · subinstâncias de {args.n} · β={params.beta:g} "
          f"γ={params.gamma:g} · ALNS {len(params.seeds)} sementes × {args.tempo:g} s\n")
    print(f"{'rep':>3} {'guloso':>9} {'ALNS':>9} {'MILP':>9} {'gap MILP':>9} {'gap gul.':>9} {'gap ALNS':>9}"
          f" {'t MILP':>8} {'visitas g/a/m':>14}")
    rows = []
    for rep in range(args.reps):
        r = {"rep": rep, **compare(subinstance(pre.instance, args.n, seed=rep), params, args.tempo_milp)}
        rows.append(r)
        gs = "—" if r["milp_gap_solver"] is None else f"{100 * r['milp_gap_solver']:.2f}%"
        print(f"{rep:>3} {r['guloso']:>9.1f} {r['alns']:>9.1f} {r['milp']:>9.1f} {gs:>9} {100 * r['gap_guloso']:>8.2f}%"
              f" {100 * r['gap_alns']:>8.2f}% {r['t_milp']:>7.1f}s"
              f" {r['visitas_guloso']:>4}/{r['visitas_alns']}/{r['visitas_milp']}")
        sys.stdout.flush()
    mean = lambda k: statistics.fmean(r[k] for r in rows)
    otimos = sum(1 for r in rows if r["milp_gap_solver"] is not None and r["milp_gap_solver"] < 1e-6)
    print(f"\nmédia: gap guloso {100 * mean('gap_guloso'):.2f}% · gap ALNS {100 * mean('gap_alns'):.2f}% · "
          f"ALNS = ótimo em {sum(1 for r in rows if r['gap_alns'] < 1e-9)}/{len(rows)} · MILP provado ótimo em "
          f"{otimos}/{len(rows)} · tempo médio MILP {mean('t_milp'):.1f} s, ALNS {mean('t_alns'):.1f} s")
    if args.csv:
        with args.csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"csv gravado em {args.csv}")


if __name__ == "__main__":
    main()
