"""
Relatório da equipe para a gestão (§6.6 da proposta): uma linha por microárea, a partir do último plano de
cada ACS na data, com a demanda que ficou de fora, a jornada usada e um alerta de sobrecarga.

Alerta de sobrecarga de uma microárea (limiares em settings.RELATORIO_LIMIARES), quando:
  - o excesso de jornada passa do limiar (o dia só coube com hora extra);
  - alguma urgência ficou sem visita;
  - a fração de domicílios atrasados que não foram visitados passa do limiar.
"""

from collections import Counter
from datetime import date

from django.conf import settings

from engine.instance import Params

from . import services
from .models import Equipe, Plano

CAMPOS_SOMADOS = ["domicilios", "atrasados", "candidatas", "planejadas", "nao_atendidas", "fora_das_candidatas",
                  "atrasados_fora", "urgentes_fora", "penalidade_residual_min", "caminhada_min", "jornada_usada_min",
                  "excesso_min"]


def _atrasado(domicilio, data: date) -> bool:
    """Mesmo critério do gerador e do engine: amanhã já terá passado o intervalo máximo."""
    return services.dias_sem_visita(domicilio, data) + 1 > domicilio.intervalo_max_dias


def linha(microarea, data: date, limiares: dict) -> dict:
    agente = getattr(microarea, "agente", None)
    doms = list(microarea.domicilios.all())
    base = {
        "microarea": {"id": microarea.pk, "nome": microarea.nome},
        "agente": {"id": agente.pk, "nome": agente.nome} if agente else None,
        "domicilios": len(doms),
        "atrasados": sum(_atrasado(d, data) for d in doms),
    }
    plano = (Plano.objects.filter(agente=agente, data=data).order_by("-criado_em").first() if agente else None)
    if plano is None:
        return {**base, "plano": None, "sem_plano": True, "alerta_sobrecarga": False, "motivos_alerta": []}

    visitados = set(plano.itens.values_list("domicilio_id", flat=True))
    por_motivo = Counter(plano.nao_atendidas.values_list("motivo", flat=True))
    atrasados_fora = sum(1 for d in doms if d.pk not in visitados and _atrasado(d, data))
    urgentes_fora = sum(1 for d in doms if d.urgente and d.pk not in visitados)
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
        "urgentes_fora": urgentes_fora,
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
        motivos.append(f"{atrasados_fora} de {len(doms)} domicílios atrasados sem visita")
    return {**row, "alerta_sobrecarga": bool(motivos), "motivos_alerta": motivos}


def relatorio(equipe: Equipe, data: date) -> dict:
    limiares = settings.RELATORIO_LIMIARES
    linhas = [linha(m, data, limiares) for m in equipe.microareas.select_related("agente").order_by("nome")]
    com_plano = [r for r in linhas if not r["sem_plano"]]
    total = {c: sum(r[c] for r in (com_plano if c not in ("domicilios", "atrasados") else linhas)) for c in CAMPOS_SOMADOS}
    total["nao_atendidas_por_motivo"] = dict(sum((Counter(r["nao_atendidas_por_motivo"]) for r in com_plano), Counter()))
    total.update({"microareas": len(linhas), "com_plano": len(com_plano), "sem_plano": len(linhas) - len(com_plano),
                  "alertas": sum(r["alerta_sobrecarga"] for r in linhas)})
    ubs = equipe.ubs
    return {
        "equipe": {"id": equipe.pk, "nome": equipe.nome},
        "ubs": {"id": ubs.pk, "nome": ubs.nome, "lat": ubs.lat, "lon": ubs.lon},
        "data": data.isoformat(),
        "limiares": limiares,
        "linhas": linhas,
        "total": total,
    }
