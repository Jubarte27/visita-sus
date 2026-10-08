"""
Planejamento do dia de um ACS a partir dos arquivos do gerador, sem banco.

    .venv/bin/python -m engine.solve data/instances/bomjesus --metodo alns [--data AAAA-MM-DD]
                                     [--beta 30 --gamma 2 --candidatas 40] [--iteracoes 1000 --tempo 5 --sementes 0,1,2,3,4]
                                     [--inicio 08:00] [--saida arquivo.json] [--export csv,gpx,geojson]

Imprime métricas e roteiro e grava a solução em <instância>/solucao.json (índices da Instance; `ids`
traduz cada índice para o id do domicílio, a linha de instance.gpkg). Com --export, grava também na pasta
da instância itinerario.csv, itinerario.gpx e rota.geojson (trajeto pela malha a pé + paradas).
"""

import argparse
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from . import export
from .instance import Params
from .io import instance_from_files
from .matrix import load_graph
from .methods import METHODS

EXPORTS = {"csv", "gpx", "geojson"}


def clock(start: datetime, minutes: float) -> str:
    return (start + timedelta(minutes=minutes)).strftime("%H:%M")


def main():
    defaults = Params()
    ap = argparse.ArgumentParser(description="Roteiro do dia de um ACS sobre uma instância do gerador.")
    ap.add_argument("instancia", type=Path, help="pasta da instância (ex.: data/instances/bomjesus)")
    ap.add_argument("--metodo", choices=sorted(METHODS), default="guloso")
    ap.add_argument("--data", type=date.fromisoformat, default=None, help="data do plano (padrão: data_base)")
    ap.add_argument("--beta", type=float, default=defaults.beta, help="min por unidade de penalidade")
    ap.add_argument("--gamma", type=float, default=defaults.gamma, help="min por min de excesso de jornada")
    ap.add_argument("--candidatas", type=int, default=defaults.n_candidatas)
    ap.add_argument("--iteracoes", type=int, default=defaults.iterations, help="iterações da ALNS por semente")
    ap.add_argument("--tempo", type=float, default=defaults.time_limit_s, help="tempo limite da ALNS por semente (s)")
    ap.add_argument("--sementes", default=",".join(map(str, defaults.seeds)), help="sementes da ALNS (ex.: 0,1,2)")
    ap.add_argument("--inicio", default="08:00", help="horário de início da jornada (HH:MM)")
    ap.add_argument("--saida", type=Path, default=None, help="arquivo da solução (padrão: <instância>/solucao.json)")
    ap.add_argument("--export", default="", help="formatos extras, separados por vírgula: csv, gpx, geojson")
    ap.add_argument("--microarea", type=int, default=None, help="microárea de uma instância de equipe (1..N)")
    args = ap.parse_args()
    formats = {f.strip() for f in args.export.split(",") if f.strip()}
    if formats - EXPORTS:
        ap.error(f"formato desconhecido em --export: {', '.join(sorted(formats - EXPORTS))}")

    params = Params(beta=args.beta, gamma=args.gamma, n_candidatas=args.candidatas, iterations=args.iteracoes,
                    time_limit_s=args.tempo, seeds=[int(x) for x in args.sementes.split(",")])
    files, pre = instance_from_files(args.instancia, args.data, params, args.microarea)
    inst, ids = pre.instance, pre.ids()
    sol = METHODS[args.metodo](inst, params)

    plan_date = args.data or files.data_base
    start = datetime.combine(plan_date, datetime.strptime(args.inicio, "%H:%M").time())
    cond = files.visits["condicao"]

    print(f"{files.path.name} · {plan_date} · método {sol.method} · β={params.beta:g} γ={params.gamma:g}")
    print(f"visitas {len(sol.stops)} de {inst.n - 1} candidatas · caminhada {sol.walk:.1f} min · "
          f"retorno {clock(start, sol.H)} (H={sol.H:.0f} de T={inst.T:.0f}/Tmax={inst.Tmax:.0f}) · excesso {sol.overtime:.0f} min")
    print(f"penalidade residual {sol.residual_penalty:.2f} (= {params.beta * sol.residual_penalty:.0f} min) · "
          f"objetivo {sol.objective:.1f} · viável {'sim' if sol.feasible else 'NÃO'} · {sol.runtime_s * 1000:.0f} ms")
    if sol.seeds_stats:
        st = sol.seeds_stats
        print(f"sementes {st['sementes']}: objetivo melhor {st['melhor']:.1f} · média {st['media']:.1f} · "
              f"desvio {st['desvio']:.2f} · pior {st['pior']:.1f} · melhor semente {sol.seed} · "
              f"{max(st['tempos_s']):.1f} s por semente (máx)")
    for v in sol.violations:
        print(f"  violação: {v.kind} {'' if v.visit is None else f'domicílio {ids[v.visit]}'} {v.amount:g}")

    print(f"\n{'#':>2}  {'domicílio':>9}  {'condição':<20} {'motivo':<8} {'chegada':>7} {'início':>6} {'fim':>5}"
          f" {'caminh.':>7}  {'w':>2} {'d/P':>7}")
    for k, st in enumerate(sol.stops, 1):
        v = inst.visits[st.visit]
        print(f"{k:>2}  {v.id:>9}  {cond[v.id]:<20} {st.reason:<8} {clock(start, st.arrival):>7} {clock(start, st.start):>6}"
              f" {clock(start, st.end):>5} {st.walk_from_prev:>6.1f}m  {v.w:>2g} {f'{v.d}/{v.P}':>7}")
    print(f"    retorno à UBS {clock(start, sol.H)} (+{inst.t[sol.route[-2], 0]:.1f} min de caminhada)")

    fora = Counter(m for _, m in sol.unvisited) + Counter(m for _, m in pre.discarded)
    print(f"\nnão atendidas: {dict(fora) or 'nenhuma'} · fora das candidatas: {len(pre.not_candidates)}")

    sufixo = f"_m{args.microarea}" if args.microarea else ""
    out = args.saida or args.instancia / f"solucao{sufixo}.json"
    out.write_text(json.dumps({
        "instancia": files.path.name, "data": plan_date.isoformat(), "inicio": args.inicio,
        "params": vars(params), "ids": ids, "solucao": sol.to_dict(),
        "descartes": pre.discarded, "fora_das_candidatas": pre.not_candidates,
    }, indent=2, ensure_ascii=False, default=float))
    print(f"solução gravada em {out}")

    if formats:
        rows = export.itinerary(inst, sol, start, files.info())
        line = export.route_line(load_graph(files.path / "graph.graphml"), inst, sol) if formats - {"csv"} else None
        name = f"{files.path.name} · {plan_date} · {sol.method}"
        written = {
            "csv": lambda p: p.write_text(export.to_csv(rows), encoding="utf-8-sig"),
            "gpx": lambda p: p.write_text(export.to_gpx(rows, line, name), encoding="utf-8"),
            "geojson": lambda p: p.write_text(json.dumps(export.to_geojson(rows, line), ensure_ascii=False), encoding="utf-8"),
        }
        names = {"csv": f"itinerario{sufixo}.csv", "gpx": f"itinerario{sufixo}.gpx", "geojson": f"rota{sufixo}.geojson"}
        for f in sorted(formats):
            path = files.path / names[f]
            written[f](path)
            print(f"{f} gravado em {path}")


if __name__ == "__main__":
    main()
