"""
Relatório da equipe para a gestão (§6.6 da proposta): uma linha por microárea, a partir do último plano de
cada ACS na data, com a demanda que ficou de fora, a jornada usada e um alerta de sobrecarga.

Alerta de sobrecarga de uma microárea (limiares em settings.RELATORIO_LIMIARES), quando:
  - o excesso de jornada passa do limiar (o dia só coube com hora extra);
  - alguma urgência ficou sem visita;
  - a fração de domicílios atrasados que não foram visitados passa do limiar.

Situação de cada microárea (`situacao`), com uma frase curta (`resumo_situacao`):
  sobrecarga  algum alerta acima;
  atencao     sem alerta, mas com hora extra ou com atrasados sem visita acima de metade do limiar;
  ok          o resto;
  sem_plano   o ACS não tem plano na data.

Indicadores para a gestão, em domicílios e dias (a penalidade em minutos equivalentes fica como detalhe técnico):
  prioritários   urgentes ou atrasados (amanhã já terá passado o intervalo máximo);
  cobertura      fração dos atrasados que foram visitados no dia;
  dias de atraso soma de max(0, d − P) dos atrasados que ficaram sem visita.
"""

import csv
import io
from collections import Counter
from datetime import date

from django.conf import settings

from engine.instance import Params

from . import services
from .models import Equipe, Plano

# campos somados em todas as linhas (descrevem a microárea) e só nas linhas com plano (descrevem o dia planejado)
CAMPOS_DA_MICROAREA = ["domicilios", "atrasados", "prioritarios"]
CAMPOS_DO_PLANO = ["candidatas", "planejadas", "nao_atendidas", "fora_das_candidatas", "atrasados_fora",
                   "atrasados_visitados", "em_dia_sem_visita", "urgentes_fora", "prioritarios_fora", "dias_atraso_fora",
                   "penalidade_residual_min", "caminhada_min", "jornada_usada_min", "excesso_min"]
CAMPOS_SOMADOS = CAMPOS_DA_MICROAREA + CAMPOS_DO_PLANO
HORA_EXTRA_MIN = 1.0  # abaixo de 1 min, o excesso é arredondamento do cronograma, não hora extra


def _atrasado(domicilio, data: date) -> bool:
    """Mesmo critério do gerador e do engine: amanhã já terá passado o intervalo máximo."""
    return services.dias_sem_visita(domicilio, data) + 1 > domicilio.intervalo_max_dias


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _juntar(itens: list[str]) -> str:
    """"a", "a e b", "a, b e c"."""
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _situacao(row: dict, n_doms: int, limiares: dict, motivos: list[str]) -> tuple[str, str]:
    if motivos:
        return "sobrecarga", _juntar(motivos)
    atencao = []
    if row["excesso_min"] >= HORA_EXTRA_MIN:
        atencao.append(f"hora extra de {row['excesso_min']:.0f} min")
    if n_doms and row["atrasados_fora"] / n_doms > limiares["fracao_atrasados_fora"] / 2:
        atencao.append(_plural(row["atrasados_fora"], "domicílio atrasado ficou", "domicílios atrasados ficaram")
                       + " sem visita")
    if atencao:
        return "atencao", _juntar(atencao)
    if row["atrasados_fora"]:
        return "ok", ("dentro da capacidade; " + _plural(row["atrasados_fora"], "atrasado fica", "atrasados ficam")
                      + " para os próximos dias")
    return "ok", "demanda do dia atendida"


def linha(microarea, data: date, limiares: dict) -> dict:
    agente = getattr(microarea, "agente", None)
    doms = list(microarea.domicilios.all())
    atrasado = {d.pk: _atrasado(d, data) for d in doms}
    base = {
        "microarea": {"id": microarea.pk, "nome": microarea.nome, "rotulo": microarea.rotulo},
        "agente": {"id": agente.pk, "nome": agente.nome} if agente else None,
        "domicilios": len(doms),
        "atrasados": sum(atrasado.values()),
        "prioritarios": sum(1 for d in doms if d.urgente or atrasado[d.pk]),
    }
    plano = (Plano.objects.filter(agente=agente, data=data).order_by("-criado_em").first() if agente else None)
    if plano is None:
        return {**base, "plano": None, "sem_plano": True, "alerta_sobrecarga": False, "motivos_alerta": [],
                "situacao": "sem_plano", "resumo_situacao": "sem plano nesta data"}

    visitados = set(plano.itens.values_list("domicilio_id", flat=True))
    por_motivo = Counter(plano.nao_atendidas.values_list("motivo", flat=True))
    fora = [d for d in doms if d.pk not in visitados]
    atrasados_fora = sum(1 for d in fora if atrasado[d.pk])
    urgentes_fora = sum(1 for d in fora if d.urgente)
    atrasados_visitados = base["atrasados"] - atrasados_fora
    dias_atraso_fora = sum(max(0, services.dias_sem_visita(d, data) - d.intervalo_max_dias)
                           for d in fora if atrasado[d.pk])
    beta = plano.params.get("beta", Params().beta)
    acs = plano.params.get("acs", {})
    row = {
        **base,
        "plano": {"id": plano.pk, "metodo": plano.metodo, "status": plano.status},
        "sem_plano": False,
        "candidatas": plano.n_candidatas,
        "planejadas": len(visitados),
        "nao_atendidas": sum(por_motivo.values()),
        "nao_atendidas_por_motivo": dict(por_motivo),
        "fora_das_candidatas": plano.n_fora_candidatas,
        "atrasados_fora": atrasados_fora,
        "atrasados_visitados": atrasados_visitados,
        "em_dia_sem_visita": len(fora) - atrasados_fora,
        "cobertura_atrasados": atrasados_visitados / base["atrasados"] if base["atrasados"] else None,
        "urgentes_fora": urgentes_fora,
        "prioritarios_fora": sum(1 for d in fora if d.urgente or atrasado[d.pk]),
        "dias_atraso_fora": dias_atraso_fora,
        "penalidade_residual": plano.penalidade_residual,
        "penalidade_residual_min": beta * plano.penalidade_residual,
        "caminhada_min": plano.caminhada_min,
        "jornada_usada_min": plano.retorno_min,
        "jornada_min": acs.get("T"),
        "jornada_max_min": acs.get("Tmax"),
        "excesso_min": plano.excesso_min,
        "retorno": services.relogio(plano, plano.retorno_min),
    }
    motivos = []
    if plano.excesso_min > limiares["excesso_min"]:
        motivos.append(f"excesso de jornada de {plano.excesso_min:.0f} min")
    if urgentes_fora:
        motivos.append(f"{urgentes_fora} urgência(s) sem visita")
    if doms and atrasados_fora / len(doms) > limiares["fracao_atrasados_fora"]:
        motivos.append(f"{atrasados_fora} domicílios atrasados sem visita ({atrasados_fora / len(doms):.0%} dos {len(doms)})")
    situacao, resumo = _situacao(row, len(doms), limiares, motivos)
    return {**row, "alerta_sobrecarga": bool(motivos), "motivos_alerta": motivos,
            "situacao": situacao, "resumo_situacao": resumo}


def resumo(linhas: list[dict], total: dict) -> str:
    """Frase para o topo do relatório: quantas microáreas dão conta do dia e quais precisam de reforço."""
    if not total["com_plano"]:
        return "Nenhum ACS tem plano para esta data."
    frases = []
    n, ok = total["com_plano"], total["com_plano"] - total["alertas"]
    if n == 1:
        frases.append("A microárea dá conta da demanda do dia." if ok else "A microárea não dá conta da demanda do dia.")
    elif ok == n:
        frases.append(f"As {n} microáreas com plano dão conta da demanda do dia.")
    elif ok == 0:
        frases.append(f"Nenhuma das {n} microáreas com plano dá conta da demanda do dia.")
    else:
        frases.append(f"{ok} das {n} microáreas com plano {'dá' if ok == 1 else 'dão'} conta da demanda do dia.")
    sobrecarga = [r for r in linhas if r["situacao"] == "sobrecarga"]
    if sobrecarga:
        itens = "; ".join(f"{r['microarea']['rotulo']}, com {r['resumo_situacao']}" for r in sobrecarga)
        frases.append(f"{'Precisa' if len(sobrecarga) == 1 else 'Precisam'} de reforço: {itens}.")
    if total["cobertura_atrasados"] is not None:
        frases.append(f"As visitas planejadas cobrem {total['cobertura_atrasados']:.0%} dos domicílios atrasados.")
    if total["sem_plano"]:
        frases.append(f"{_plural(total['sem_plano'], 'microárea está', 'microáreas estão')} sem plano nesta data.")
    return " ".join(frases)


def relatorio(equipe: Equipe, data: date) -> dict:
    limiares = settings.RELATORIO_LIMIARES
    linhas = [linha(m, data, limiares) for m in equipe.microareas.select_related("agente").order_by("nome")]
    com_plano = [r for r in linhas if not r["sem_plano"]]
    total = {c: sum(r[c] for r in linhas) for c in CAMPOS_DA_MICROAREA}
    total |= {c: sum(r[c] for r in com_plano) for c in CAMPOS_DO_PLANO}
    total["nao_atendidas_por_motivo"] = dict(sum((Counter(r["nao_atendidas_por_motivo"]) for r in com_plano), Counter()))
    atrasados_com_plano = sum(r["atrasados"] for r in com_plano)
    total.update({
        "microareas": len(linhas), "com_plano": len(com_plano), "sem_plano": len(linhas) - len(com_plano),
        "alertas": sum(r["alerta_sobrecarga"] for r in linhas),
        "acs_com_hora_extra": sum(r["excesso_min"] >= HORA_EXTRA_MIN for r in com_plano),
        "excesso_max_min": max((r["excesso_min"] for r in com_plano), default=0.0),
        "caminhada_media_min": total["caminhada_min"] / len(com_plano) if com_plano else None,
        "cobertura_atrasados": total["atrasados_visitados"] / atrasados_com_plano if atrasados_com_plano else None,
    })
    ubs = equipe.ubs
    return {
        "equipe": {"id": equipe.pk, "nome": equipe.nome},
        "ubs": {"id": ubs.pk, "nome": ubs.nome, "lat": ubs.lat, "lon": ubs.lon},
        "data": data.isoformat(),
        "limiares": limiares,
        "resumo": resumo(linhas, total),
        "linhas": linhas,
        "total": total,
    }


ROTULO_SITUACAO = {"ok": "ok", "atencao": "atenção", "sobrecarga": "sobrecarga", "sem_plano": "sem plano"}
CSV_CAMPOS = [
    ("microarea", "microárea"), ("acs", "ACS"), ("situacao", "situação"), ("resumo_situacao", "observação"),
    ("domicilios", "domicílios"), ("atrasados", "atrasados"), ("planejadas", "visitas no dia"),
    ("cobertura_atrasados", "cobertura dos atrasados (%)"), ("atrasados_fora", "atrasados sem visita"),
    ("urgentes_fora", "urgências sem visita"), ("dias_atraso_fora", "dias de atraso acumulados"),
    ("nao_atendidas", "candidatas não atendidas"), ("caminhada_min", "caminhada (min)"), ("retorno", "retorno à UBS"),
    ("excesso_min", "hora extra (min)"), ("penalidade_residual_min", "penalidade residual (min equivalentes)"),
    ("plano", "plano"),
]


def _csv_linha(r: dict, nome: str, acs: str) -> dict:
    def num(v, casas=0):
        return "" if v is None else f"{v:.{casas}f}"

    cobertura = r.get("cobertura_atrasados")
    return {
        "microarea": nome, "acs": acs, "situacao": ROTULO_SITUACAO.get(r.get("situacao"), ""),
        "resumo_situacao": r.get("resumo_situacao", ""), "domicilios": r["domicilios"], "atrasados": r["atrasados"],
        "planejadas": r.get("planejadas", ""), "cobertura_atrasados": num(None if cobertura is None else 100 * cobertura),
        "atrasados_fora": r.get("atrasados_fora", ""), "urgentes_fora": r.get("urgentes_fora", ""),
        "dias_atraso_fora": r.get("dias_atraso_fora", ""), "nao_atendidas": r.get("nao_atendidas", ""),
        "caminhada_min": num(r.get("caminhada_min")), "retorno": r.get("retorno", ""),
        "excesso_min": num(r.get("excesso_min")), "penalidade_residual_min": num(r.get("penalidade_residual_min")),
        "plano": (r.get("plano") or {}).get("id", ""),
    }


def to_csv(rel: dict) -> str:
    """Relatório em CSV (vírgula, decimais com ponto), uma linha por microárea mais o total da equipe."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[c for c, _ in CSV_CAMPOS], lineterminator="\n")
    writer.writerow(dict(CSV_CAMPOS))
    for r in rel["linhas"]:
        writer.writerow(_csv_linha(r, r["microarea"]["rotulo"], (r["agente"] or {}).get("nome", "")))
    t = rel["total"]
    writer.writerow(_csv_linha({**t, "situacao": None, "resumo_situacao": rel["resumo"], "retorno": "",
                                "caminhada_min": t["caminhada_min"]},
                               "Total da equipe", f"{t['microareas']} ACS"))
    return buf.getvalue()


def nome_arquivo(rel: dict) -> str:
    return f"relatorio_{rel['equipe']['nome'].replace(' ', '_')}_{rel['data']}.csv"
