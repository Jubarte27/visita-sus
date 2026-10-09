"""
Gráficos e tabelas da validação (P16), a partir dos CSVs de backend/data/resultados/.

    .venv/bin/python -m engine.graficos [--resultados data/resultados] [--saida ../docs/resultados]

Grava PNGs para os slides e `tabelas.md` (as mesmas informações em tabela: os gráficos nunca são a única fonte).
Estilo: paleta categórica fixa (guloso, ALNS, MILP sempre nas mesmas cores), um eixo por gráfico, traços finos,
grade discreta, texto nas cores de texto.
"""

import argparse
import csv
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
COR = {"guloso": "#2a78d6", "alns": "#eb6834", "milp": "#1baf7a"}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
TEXTO, TEXTO_2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
ROTULO = {"base": "base", "aglomerado": "aglomerado", "alta_urgencia": "alta urgência", "alto_atraso": "alto atraso",
          "equipe_4acs": "equipe 4 ACS"}
NOME = {"guloso": "guloso", "alns": "ALNS", "milp": "MILP"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO_2,
    "axes.titlecolor": TEXTO, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": TEXTO_2, "ytick.color": TEXTO_2, "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.labelcolor": TEXTO,
})


def ler(caminho: Path) -> list[dict]:
    with caminho.open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v) if v not in ("", "True", "False") else (v == "True" if v else None)
            except ValueError:
                pass
    return rows


def media(xs):
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else float("nan")


def _salvar(fig, saida: Path, nome: str):
    fig.tight_layout()
    fig.savefig(saida / nome, dpi=200)
    plt.close(fig)
    print(f"gráfico {saida / nome}")


def resumo_validacao(rows: list[dict]) -> list[dict]:
    """Uma linha por cenário (a equipe soma/agrega as microáreas)."""
    out = []
    for c in ROTULO:
        comp = [r for r in rows if r["cenario"] == c and r["escopo"] == "completa"]
        sub = [r for r in rows if r["cenario"] == c and r["escopo"] == "sub"]
        if not comp:
            continue
        unidades = sorted({r["microarea"] for r in comp}, key=str)
        g = [r for r in comp if r["metodo"] == "guloso"]
        a = [r for r in comp if r["metodo"] == "alns"]
        melhorias, melhores, desvios, medios = [], [], [], []
        for u in unidades:
            gu = next(r for r in g if r["microarea"] == u)["objetivo"]
            au = [r["objetivo"] for r in a if r["microarea"] == u]
            melhores.append(min(au))
            medios.append(statistics.fmean(au))
            desvios.append(statistics.pstdev(au))
            melhorias += [(x - gu) / gu for x in au]
        a_best = [min((r for r in a if r["microarea"] == u), key=lambda r: r["objetivo"]) for u in unidades]
        subs_alns = [r for r in sub if r["metodo"] == "alns"]
        otimo = sum(1 for r in subs_alns if r["gap_milp"] is not None and r["gap_milp"] < 1e-9)
        out.append({
            "cenario": c, "unidades": len(unidades), "candidatas": sum(r["candidatas"] for r in g),
            "guloso": sum(r["objetivo"] for r in g), "alns_melhor": sum(melhores), "alns_medio": sum(medios),
            "alns_desvio": media(desvios), "melhoria_media": media(melhorias), "melhoria_min": min(melhorias),
            "melhoria_max": max(melhorias),
            "visitas_guloso": sum(r["visitas"] for r in g), "visitas_alns": sum(r["visitas"] for r in a_best),
            "caminhada_guloso": sum(r["caminhada_min"] for r in g), "caminhada_alns": sum(r["caminhada_min"] for r in a_best),
            "excesso_guloso": sum(r["excesso_min"] for r in g), "excesso_alns": sum(r["excesso_min"] for r in a_best),
            "atrasados_fora_alns": sum(r["atrasados_fora"] for r in a_best),
            "atrasados_candidatas": sum(r["atrasados_candidatas"] for r in g),
            "urgentes": sum(r["urgentes"] for r in g), "urgentes_atendidas": sum(r["urgentes_atendidas"] for r in a_best),
            "urgencia_excedente": sum(r["urgencia_excedente"] for r in g),
            "urgencias_primeiro": all(r["urgencias_primeiro"] for r in comp),
            "viaveis": all(r["viavel"] for r in rows if r["cenario"] == c),
            "t_alns_s": media([r["runtime_s"] for r in a]), "t_guloso_s": media([r["runtime_s"] for r in g]),
            "gap_guloso": media([r["gap_milp"] for r in sub if r["metodo"] == "guloso"]),
            "gap_alns": media([r["gap_milp"] for r in subs_alns]),
            "gap_alns_max": max((r["gap_milp"] for r in subs_alns), default=float("nan")),
            "alns_otimo": f"{otimo}/{len(subs_alns)}",
            "milp_provado": sum(1 for r in sub if r["metodo"] == "milp" and r["gap_solver"] is not None and r["gap_solver"] < 1e-5),
            "milp_n": sum(1 for r in sub if r["metodo"] == "milp"),
            "t_milp_s": media([r["runtime_s"] for r in sub if r["metodo"] == "milp"]),
        })
    return out


def grafico_gap(res, saida):
    fig, ax = plt.subplots(figsize=(8, 4))
    xs = range(len(res))
    w = 0.32
    for k, m in enumerate(["guloso", "alns"]):
        vals = [100 * r[f"gap_{m}"] for r in res]
        pos = [x + (k - 0.5) * (w + 0.04) for x in xs]
        bars = ax.bar(pos, vals, width=w, color=COR[m], label=NOME[m])
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:.2f}%", (b.get_x() + b.get_width() / 2, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8, color=TEXTO)
    ax.set_xticks(list(xs), [ROTULO[r["cenario"]] for r in res])
    ax.set_ylabel("gap médio para o ótimo (MILP), %")
    ax.set_title("Distância ao ótimo em subinstâncias de 10 candidatas")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left")
    _salvar(fig, saida, "gap_milp.png")


def grafico_melhoria(res, saida):
    fig, ax = plt.subplots(figsize=(8, 4))
    ys = list(range(len(res)))[::-1]
    for y, r in zip(ys, res):
        m, lo, hi = (-100 * r["melhoria_media"], -100 * r["melhoria_max"], -100 * r["melhoria_min"])
        ax.barh(y, m, height=0.45, color=COR["alns"])
        ax.plot([lo, hi], [y, y], color=TEXTO_2, linewidth=1.2)
        ax.annotate(f"{m:.1f}%", (max(hi, m), y), xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=9, color=TEXTO)
    ax.set_yticks(ys, [ROTULO[r["cenario"]] for r in res])
    ax.set_xlabel("redução do objetivo em relação ao guloso, % (barra = média; traço = pior e melhor semente)")
    ax.set_title("ALNS × construção gulosa, instâncias completas")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(-100 * r["melhoria_min"] for r in res) * 1.25)
    _salvar(fig, saida, "melhoria_alns.png")


def grafico_sementes(rows, saida):
    fig, ax = plt.subplots(figsize=(8, 4))
    ys = []
    for y, c in enumerate(reversed(list(ROTULO))):
        comp = [r for r in rows if r["cenario"] == c and r["escopo"] == "completa" and r["metodo"] == "alns"]
        if not comp:
            continue
        pts = []
        for u in sorted({r["microarea"] for r in comp}, key=str):
            au = [r["objetivo"] for r in comp if r["microarea"] == u]
            pts += [100 * (x - min(au)) / min(au) for x in au]
        ax.scatter(pts, [y] * len(pts), s=40, color=COR["alns"], alpha=0.75, edgecolors=FUNDO, linewidths=1.5)
        ys.append((y, c))
    ax.set_yticks([y for y, _ in ys], [ROTULO[c] for _, c in ys])
    ax.set_xlabel("objetivo de cada semente acima da melhor semente, %")
    ax.set_title("Variação entre as 10 sementes da ALNS")
    ax.grid(axis="y", visible=False)
    _salvar(fig, saida, "sementes.png")


def grafico_calibracao_pesos(rows, saida):
    betas = sorted({r["beta"] for r in rows})
    gammas = sorted({r["gamma"] for r in rows})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, chave, titulo, unidade in [(axes[0], "excesso_min", "Excesso de jornada", "min"),
                                       (axes[1], "visitas", "Visitas no dia", "visitas")]:
        for k, b in enumerate(betas):
            ys = [media([r[chave] for r in rows if r["beta"] == b and r["gamma"] == g]) for g in gammas]
            ax.plot(gammas, ys, color=SERIES[k], linewidth=2, marker="o", markersize=6, label=f"β = {b:g}")
            ax.annotate(f"β={b:g}", (gammas[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                        fontsize=8, color=TEXTO)
        ax.set_xscale("log")
        ax.set_xticks(gammas, [f"{g:g}" for g in gammas])
        ax.minorticks_off()
        ax.set_xlabel("γ (min por min de excesso)")
        ax.set_ylabel(unidade)
        ax.set_title(titulo)
    axes[0].axvline(20, color=TEXTO_2, linewidth=1, linestyle="--")
    axes[0].annotate("escolhido: β=30, γ=20", (20, axes[0].get_ylim()[1] * 0.92), xytext=(-6, 0),
                     textcoords="offset points", ha="right", fontsize=8, color=TEXTO_2)
    axes[0].legend(loc="lower left")
    _salvar(fig, saida, "calibracao_pesos.png")


def grafico_taguchi(rows, saida):
    fatores = [("nivel_d", "destruicao", "destruição (fração)"), ("nivel_t", "t_inicial", "temperatura inicial"),
               ("nivel_r", "resfriamento", "resfriamento")]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
    for ax, (nivel, rotulo, titulo) in zip(axes, fatores):
        niveis = sorted({int(r[nivel]) for r in rows})
        nomes = [next(str(r[rotulo]) for r in rows if int(r[nivel]) == n) for n in niveis]
        ys = [100 * media([r["gap_melhor"] for r in rows if int(r[nivel]) == n]) for n in niveis]
        ax.plot(range(len(niveis)), ys, color=COR["alns"], linewidth=2, marker="o", markersize=7)
        ax.set_xticks(range(len(niveis)), [n.replace(".0", "") for n in nomes])
        ax.set_title(titulo, fontsize=10)
        ax.set_xlim(-0.4, len(niveis) - 0.6)
    axes[0].set_ylabel("gap médio para a melhor solução, %")
    fig.suptitle("Calibração da ALNS (Taguchi L9): efeitos principais", x=0.01, ha="left", fontweight="bold",
                 color=TEXTO)
    _salvar(fig, saida, "taguchi.png")


def tabelas(res, pesos, alns_rows, saida):
    L = ["<!-- gerado por python -m engine.graficos; não editar à mão -->", "",
         "### Instâncias completas (ALNS: 10 sementes; equipe = soma das 4 microáreas)", "",
         "| cenário | candidatas | guloso | ALNS melhor | ALNS média ± desvio | redução média (pior–melhor) | visitas g/a | caminhada g/a (min) | excesso g/a (min) | t ALNS/semente |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res:
        L.append(f"| {ROTULO[r['cenario']]} | {r['candidatas']:.0f} | {r['guloso']:.1f} | {r['alns_melhor']:.1f} | "
                 f"{r['alns_medio']:.1f} ± {r['alns_desvio']:.1f} | {-100 * r['melhoria_media']:.2f}% "
                 f"({-100 * r['melhoria_min']:.2f}–{-100 * r['melhoria_max']:.2f}%) | {r['visitas_guloso']:.0f}/{r['visitas_alns']:.0f} | "
                 f"{r['caminhada_guloso']:.0f}/{r['caminhada_alns']:.0f} | {r['excesso_guloso']:.0f}/{r['excesso_alns']:.0f} | {r['t_alns_s']:.1f} s |")
    L += ["", "### Regras clínicas e demanda (melhor semente da ALNS)", "",
          "| cenário | urgentes atendidas | urgências excedentes (fora da jornada) | urgências primeiro | atrasados entre as candidatas | atrasados não visitados | planos viáveis |",
          "|---|---|---|---|---|---|---|"]
    for r in res:
        L.append(f"| {ROTULO[r['cenario']]} | {r['urgentes_atendidas']:.0f}/{r['urgentes']:.0f} | {r['urgencia_excedente']:.0f} | "
                 f"{'sim' if r['urgencias_primeiro'] else 'NÃO'} | {r['atrasados_candidatas']:.0f} | {r['atrasados_fora_alns']:.0f} | "
                 f"{'todos' if r['viaveis'] else 'NÃO'} |")
    L += ["", "### Subinstâncias de 10 candidatas × MILP (5 sorteios por cenário/microárea; ALNS: 10 sementes)", "",
          "| cenário | MILP ótimo provado | t MILP | gap médio guloso | gap médio ALNS | pior gap ALNS | ALNS = ótimo |",
          "|---|---|---|---|---|---|---|"]
    for r in res:
        L.append(f"| {ROTULO[r['cenario']]} | {r['milp_provado']}/{r['milp_n']} | {r['t_milp_s']:.2f} s | "
                 f"{100 * r['gap_guloso']:.2f}% | {100 * r['gap_alns']:.2f}% | {100 * r['gap_alns_max']:.2f}% | {r['alns_otimo']} |")
    if pesos:
        L += ["", "### Calibração de β e γ (ALNS, 4 cenários × 3 sementes; médias)", "",
              "| β | γ | excesso (min) | visitas | penalidade residual | atrasados não visitados |", "|---|---|---|---|---|---|"]
        for b in sorted({r["beta"] for r in pesos}):
            for g in sorted({r["gamma"] for r in pesos}):
                sel = [r for r in pesos if r["beta"] == b and r["gamma"] == g]
                L.append(f"| {b:g} | {g:g} | {media([r['excesso_min'] for r in sel]):.1f} | {media([r['visitas'] for r in sel]):.1f} | "
                         f"{media([r['penalidade_residual'] for r in sel]):.1f} | {media([r['atrasados_fora'] for r in sel]):.1f} |")
    if alns_rows:
        L += ["", "### Calibração da ALNS (Taguchi L9; β=30, γ=20; 3 cenários × 5 sementes)", "",
              "| config | destruição | T0 | resfriamento | gap médio | pior |", "|---|---|---|---|---|---|"]
        for k in sorted({int(r["config"]) for r in alns_rows}):
            sel = [r for r in alns_rows if int(r["config"]) == k]
            L.append(f"| {k} | {sel[0]['destruicao']} | {sel[0]['t_inicial']:g} | {sel[0]['resfriamento']:g} | "
                     f"{100 * media([r['gap_melhor'] for r in sel]):.3f}% | {100 * max(r['gap_melhor'] for r in sel):.2f}% |")
    (saida / "tabelas.md").write_text("\n".join(L) + "\n")
    print(f"tabelas {saida / 'tabelas.md'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resultados", type=Path, default=BASE / "data" / "resultados")
    ap.add_argument("--saida", type=Path, default=BASE.parent / "docs" / "resultados")
    args = ap.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)
    rows = ler(args.resultados / "validacao.csv")
    res = resumo_validacao(rows)
    grafico_gap(res, args.saida)
    grafico_melhoria(res, args.saida)
    grafico_sementes(rows, args.saida)
    pesos = ler(args.resultados / "calibracao_pesos.csv") if (args.resultados / "calibracao_pesos.csv").exists() else []
    alns_rows = ler(args.resultados / "calibracao_alns.csv") if (args.resultados / "calibracao_alns.csv").exists() else []
    if pesos:
        grafico_calibracao_pesos(pesos, args.saida)
    if alns_rows:
        grafico_taguchi(alns_rows, args.saida)
    tabelas(res, pesos, alns_rows, args.saida)


if __name__ == "__main__":
    main()
