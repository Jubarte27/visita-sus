"""
Calibração preliminar (§6.8 da proposta), em duas etapas. As rodadas são independentes e rodam em paralelo;
a ALNS para por nº de iterações (o tempo limite é folgado), para o resultado não depender da carga da máquina.

1. Pesos β e γ (grade): β e γ definem o próprio objetivo, então não dá para escolhê-los pelo valor do
   objetivo. Cada par é julgado pelo plano que produz: excesso de jornada, visitas, penalidade residual
   (sem o β), atrasados e urgências que ficam de fora.

       .venv/bin/python -m engine.calibrate pesos --cenarios base=data/instances/bomjesus,...

2. Parâmetros da ALNS (Taguchi L9: 3 fatores × 3 níveis em 9 configurações): taxa de destruição,
   temperatura inicial e resfriamento, com β e γ fixos. Resposta: gap do objetivo para a melhor solução
   conhecida do cenário (menor é melhor), média sobre sementes e cenários; efeitos principais por fator.

       .venv/bin/python -m engine.calibrate alns --beta 30 --gamma 10 --cenarios ...
"""

import argparse
import csv
import os
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from . import alns, greedy
from .instance import Params
from .io import instance_from_files

RESULTADOS = Path(__file__).resolve().parent.parent / "data" / "resultados"
BETAS = [10, 30, 60]
GAMMAS = [2, 5, 10, 20]
# níveis dos fatores da ALNS e o arranjo ortogonal L9 (colunas 1–3)
DESTRUICAO = [(0.05, 0.20), (0.10, 0.40), (0.20, 0.50)]
TEMPERATURA = [10.0, 50.0, 200.0]
RESFRIAMENTO = [0.99, 0.995, 0.999]
L9 = [(0, 0, 0), (0, 1, 1), (0, 2, 2), (1, 0, 1), (1, 1, 2), (1, 2, 0), (2, 0, 2), (2, 1, 0), (2, 2, 1)]

_cache = {}


def _instancia(caminho: str, microarea: int | None = None):
    chave = (caminho, microarea)
    if chave not in _cache:
        _cache[chave] = instance_from_files(caminho, microarea=microarea)[1]
    return _cache[chave]


def metricas_do_plano(pre, sol) -> dict:
    """Métricas de resultado de um plano (independentes de β e γ)."""
    inst = pre.instance
    fora = [i for i, _ in sol.unvisited]
    return {
        "objetivo": sol.objective, "visitas": len(sol.stops), "caminhada_min": sol.walk, "retorno_min": sol.H,
        "excesso_min": sol.overtime, "penalidade_residual": sol.residual_penalty,
        "atrasados_fora": sum(inst.visits[i].overdue for i in fora),
        "urgentes_fora": sum(inst.visits[i].urgent for i in fora) + sum(m == "urgencia_excedente" for _, m in pre.discarded),
        "graves_visitados": sum(inst.visits[st.visit].grave for st in sol.stops),
        "viavel": sol.feasible, "runtime_s": sol.runtime_s,
    }


def _rodar(tarefa):
    cenario, caminho, params, semente, rotulo = tarefa
    pre = _instancia(caminho)
    inicial = greedy.solve(pre.instance, params).route
    sol = alns.solve(pre.instance, params, initial=inicial, seed=semente)
    return {"cenario": cenario, **rotulo, "semente": semente, **metricas_do_plano(pre, sol)}


def _executar(tarefas, workers):
    with ProcessPoolExecutor(workers) as pool:
        return list(pool.map(_rodar, tarefas, chunksize=1))


def _gravar(linhas, caminho: Path):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"csv gravado em {caminho}")


def calibrar_pesos(cenarios: dict, sementes: list[int], base: Params, workers: int) -> list[dict]:
    tarefas = [(c, p, replace(base, beta=b, gamma=g), s, {"beta": b, "gamma": g})
               for c, p in cenarios.items() for b in BETAS for g in GAMMAS for s in sementes]
    linhas = _executar(tarefas, workers)
    print(f"\n{'β':>4} {'γ':>4} | {'excesso':>8} {'visitas':>8} {'pen.resid.':>10} {'atras.fora':>10} {'urg.fora':>8}"
          f"   (média sobre {len(cenarios)} cenários × {len(sementes)} sementes)")
    for b in BETAS:
        for g in GAMMAS:
            sel = [r for r in linhas if r["beta"] == b and r["gamma"] == g]
            m = lambda k: statistics.fmean(r[k] for r in sel)
            print(f"{b:>4} {g:>4} | {m('excesso_min'):>7.1f}m {m('visitas'):>8.1f} {m('penalidade_residual'):>10.1f}"
                  f" {m('atrasados_fora'):>10.1f} {m('urgentes_fora'):>8.1f}")
    return linhas


def calibrar_alns(cenarios: dict, sementes: list[int], base: Params, workers: int) -> list[dict]:
    tarefas = []
    for k, (a, b, c) in enumerate(L9, 1):
        p = replace(base, destroy_min=DESTRUICAO[a][0], destroy_max=DESTRUICAO[a][1], t_start=TEMPERATURA[b],
                    cooling=RESFRIAMENTO[c])
        rot = {"config": k, "destruicao": f"{DESTRUICAO[a][0]}–{DESTRUICAO[a][1]}", "t_inicial": TEMPERATURA[b],
               "resfriamento": RESFRIAMENTO[c], "nivel_d": a, "nivel_t": b, "nivel_r": c}
        tarefas += [(cn, cp, p, s, rot) for cn, cp in cenarios.items() for s in sementes]
    linhas = _executar(tarefas, workers)
    melhor = {c: min(r["objetivo"] for r in linhas if r["cenario"] == c) for c in cenarios}
    for r in linhas:
        r["gap_melhor"] = (r["objetivo"] - melhor[r["cenario"]]) / melhor[r["cenario"]]
    print(f"\n{'cfg':>3} {'destruição':>11} {'T0':>6} {'resfr.':>6} | {'gap médio':>9} {'pior':>7}")
    for k in range(1, 10):
        sel = [r for r in linhas if r["config"] == k]
        print(f"{k:>3} {sel[0]['destruicao']:>11} {sel[0]['t_inicial']:>6g} {sel[0]['resfriamento']:>6g} |"
              f" {100 * statistics.fmean(r['gap_melhor'] for r in sel):>8.3f}% {100 * max(r['gap_melhor'] for r in sel):>6.2f}%")
    print("\nefeitos principais (gap médio por nível):")
    for nome, chave, niveis in [("destruição", "nivel_d", DESTRUICAO), ("T0", "nivel_t", TEMPERATURA),
                                ("resfriamento", "nivel_r", RESFRIAMENTO)]:
        efeitos = [statistics.fmean(r["gap_melhor"] for r in linhas if r[chave] == n) for n in range(3)]
        print(f"  {nome:>12}: " + "  ".join(f"{niveis[n]}: {100 * e:.3f}%" for n, e in enumerate(efeitos)))
    return linhas


def _cenarios(texto: str) -> dict:
    return dict(item.split("=", 1) for item in texto.split(","))


def main():
    d = Params()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etapa", choices=["pesos", "alns"])
    ap.add_argument("--cenarios", required=True, help="nome=pasta,nome=pasta,...")
    ap.add_argument("--sementes", default="0,1,2")
    ap.add_argument("--beta", type=float, default=d.beta)
    ap.add_argument("--gamma", type=float, default=d.gamma)
    ap.add_argument("--iteracoes", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--saida", type=Path, default=None)
    args = ap.parse_args()
    base = Params(beta=args.beta, gamma=args.gamma, iterations=args.iteracoes, time_limit_s=60.0)
    sementes = [int(s) for s in args.sementes.split(",")]
    cenarios = _cenarios(args.cenarios)
    for caminho in cenarios.values():
        _instancia(caminho)  # calcula matrix.npz antes de abrir os processos
    fn = calibrar_pesos if args.etapa == "pesos" else calibrar_alns
    linhas = fn(cenarios, sementes, base, args.workers)
    _gravar(linhas, args.saida or RESULTADOS / f"calibracao_{args.etapa}.csv")


if __name__ == "__main__":
    main()
