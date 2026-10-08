"""
Importação das instâncias do gerador para o banco.

Uma instância vira uma Microarea com seu Agente e seus Domicílios, dentro de uma Equipe de uma UBS
(reutilizadas pela coordenada da UBS e pelo nome da equipe). A importação é idempotente: reimportar a
mesma instância (mesmo nome) atualiza os registros em vez de duplicar; domicílios que sumiram do arquivo
são removidos, a menos que algum plano dependa deles.
"""

from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
from django.conf import settings
from django.db import transaction
from django.db.models import ProtectedError
from shapely.geometry import mapping

from engine.io import ensure_matrix, load_instance_files

from .models import Agente, Domicilio, Equipe, Microarea, Ubs


class ImportacaoError(Exception):
    pass


def _relative_dir(path: Path) -> str:
    """Pasta da instância relativa a INSTANCES_DIR quando estiver dentro dela; senão, absoluta."""
    path = path.resolve()
    try:
        return str(path.relative_to(Path(settings.INSTANCES_DIR).resolve()))
    except ValueError:
        return str(path)


def _poligono(path: Path) -> dict | None:
    """União dos setores da camada `microarea` (GeoJSON em lon/lat), se existir."""
    try:
        setores = gpd.read_file(path / "instance.gpkg", layer="microarea").to_crs(4326)
    except Exception:
        return None
    return mapping(setores.union_all()) if len(setores) else None


def _poligonos_equipe(path: Path) -> dict[int, dict]:
    """Polígono (GeoJSON) de cada microárea de uma instância de equipe (camada `microareas`)."""
    regs = gpd.read_file(path / "instance.gpkg", layer="microareas").to_crs(4326)
    return {int(r.microarea): mapping(r.geometry) for r in regs.itertuples()}


@transaction.atomic
def importar_instancia(path: str | Path, equipe: str | None = None, agente: str | None = None,
                       data_base: date | None = None, ubs_nome: str | None = None) -> list[Microarea]:
    """
    Importa uma instância e devolve as microáreas criadas ou atualizadas: uma, ou N se a instância for de equipe
    (gerador com --acs N: meta.equipe + coluna `microarea` em visits). Numa equipe, as microáreas se chamam
    <instância>_<k>, compartilham grafo e matriz, e o padrão da equipe é "eSF <instância>".
    """
    path = Path(path)
    if not (path / "meta.json").exists():
        raise ImportacaoError(f"{path} não é uma instância do gerador (falta meta.json)")
    files = load_instance_files(path)
    ensure_matrix(files)
    meta, visits = files.meta, files.visits
    nome = meta.get("nome") or path.name
    mi = meta.get("microarea", {})
    bairros = mi.get("bairros") or []
    equipe_meta = meta.get("equipe")

    ubs_geom = visits.geometry.iloc[0]
    ubs_lat = round(meta.get("ubs", {}).get("lat", ubs_geom.y), 7)
    ubs_lon = round(meta.get("ubs", {}).get("lon", ubs_geom.x), 7)
    ubs, _ = Ubs.objects.get_or_create(lat=ubs_lat, lon=ubs_lon,
                                       defaults={"nome": ubs_nome or f"UBS {bairros[0] if bairros else nome}"})
    if ubs_nome and ubs.nome != ubs_nome:
        ubs.nome = ubs_nome
        ubs.save(update_fields=["nome"])
    padrao = f"eSF {nome}" if equipe_meta else f"eSF {bairros[0] if bairros else nome}"
    equipe_obj, _ = Equipe.objects.get_or_create(ubs=ubs, nome=equipe or padrao)

    base = data_base or files.data_base
    if not equipe_meta:
        return [_importar_microarea(files, base, nome, equipe_obj, _poligono(path), mi, list(visits.index[1:]),
                                    agente or f"ACS {nome}", explicit_agent=agente is not None)]
    if "microarea" not in visits.columns:
        raise ImportacaoError(f"{path}: meta.json descreve uma equipe, mas visits não tem a coluna microarea")
    polys = _poligonos_equipe(path)
    out = []
    for info in equipe_meta["microareas"]:
        k = int(info["id"])
        codigos = [i for i in visits.index[1:] if int(visits.at[i, "microarea"]) == k]
        out.append(_importar_microarea(files, base, f"{nome}_{k}", equipe_obj, polys.get(k), info, codigos,
                                       f"{agente} {k}" if agente else f"ACS {nome} {k}",
                                       explicit_agent=agente is not None))
    return out


def _importar_microarea(files, base: date, nome: str, equipe_obj: Equipe, poligono, info: dict, codigos: list[int],
                        nome_agente: str, explicit_agent: bool) -> Microarea:
    path, meta, visits = files.path, files.meta, files.visits
    microarea, _ = Microarea.objects.update_or_create(nome=nome, defaults={
        "equipe": equipe_obj,
        "setores": info.get("setores", []),
        "bairros": info.get("bairros") or [],
        "poligono": poligono,
        "area_km2": info.get("area_km2"),
        "moradores_censo": info.get("moradores_censo"),
        "domicilios_censo": info.get("domicilios_censo"),
        "instancia_dir": _relative_dir(path),
        "ubs_node": files.ubs_node,
        "meta": {**meta, "microarea": info},
    })

    acs = meta.get("acs", {})
    defaults = {k: acs[k] for k in ("jornada_min", "jornada_max_min", "velocidade_m_min", "teto_graves") if k in acs}
    agente_obj, created = Agente.objects.get_or_create(microarea=microarea, defaults={"nome": nome_agente, **defaults})
    if not created:
        for k, v in {**defaults, **({"nome": nome_agente} if explicit_agent else {})}.items():
            setattr(agente_obj, k, v)
        agente_obj.save()

    existing = {d.codigo: d for d in microarea.domicilios.all()}
    fields = ["node", "lat", "lon", "edificacao", "n_moradores", "condicao", "peso", "intervalo_max_dias",
              "duracao_min", "ultima_visita", "tw_inicio", "tw_fim", "urgente", "grave"]
    to_create, to_update = [], []
    cols = set(visits.columns)
    for codigo in codigos:
        r = visits.loc[codigo]
        codigo = int(codigo)
        values = {
            "node": int(r.node), "lat": r.geometry.y, "lon": r.geometry.x,
            "edificacao": int(r.edificacao) if "edificacao" in cols else None,
            "n_moradores": int(r.n_moradores) if "n_moradores" in cols else 1,
            "condicao": r.condicao, "peso": float(r.w), "intervalo_max_dias": int(r.P), "duracao_min": float(r.s),
            "ultima_visita": base - timedelta(days=int(r.d)),
            "tw_inicio": float(r.tw_start), "tw_fim": float(r.tw_end),
            "urgente": bool(r.urgente), "grave": bool(r.grave),
        }
        if codigo in existing:
            obj = existing[codigo]
            for k, v in values.items():
                setattr(obj, k, v)
            to_update.append(obj)
        else:
            to_create.append(Domicilio(microarea=microarea, codigo=codigo, **values))
    Domicilio.objects.bulk_create(to_create, batch_size=1000)
    Domicilio.objects.bulk_update(to_update, fields, batch_size=1000)

    seen = {int(c) for c in codigos}
    gone = [c for c in existing if c not in seen]
    if gone:
        try:
            microarea.domicilios.filter(codigo__in=gone).delete()
        except ProtectedError:
            raise ImportacaoError(
                f"{len(gone)} domicílio(s) de {nome} sumiram do arquivo, mas há planos que dependem deles; "
                "apague esses planos antes de reimportar") from None
    return microarea
