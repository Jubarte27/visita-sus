"""
Saídas do itinerário de um ACS (módulo M5 da proposta): CSV, GPX e GeoJSON.

O itinerário (`itinerary`) junta a Solution com os dados de cada domicílio (`info`: id → condição e
coordenadas), vindos dos arquivos do gerador ou do banco, e converte os minutos da jornada em horários.
A rota é desenhada pela malha a pé (`route_line`), trecho a trecho, com `matrix.leg_path`.
"""

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timedelta

import gpxpy.gpx
from shapely.geometry import LineString, mapping

from .instance import Instance, Solution
from .matrix import leg_path

UBS_ID = -1
CSV_FIELDS = ["ordem", "domicilio", "condicao", "motivo", "chegada", "inicio", "fim", "espera_min", "caminhada_min",
              "duracao_min", "w", "d", "P", "lat", "lon"]


@dataclass
class ItineraryRow:
    ordem: int
    domicilio: int               # -1 = UBS (linha de retorno)
    condicao: str
    motivo: str                  # urgencia | atraso | risco | rotina | retorno
    chegada: datetime
    inicio: datetime
    fim: datetime
    espera_min: float
    caminhada_min: float         # desde a parada anterior
    duracao_min: float
    w: float
    d: int
    P: int
    lat: float
    lon: float

    def as_csv(self) -> dict:
        row = {f: getattr(self, f) for f in CSV_FIELDS}
        for f in ("chegada", "inicio", "fim"):
            row[f] = row[f].strftime("%H:%M")
        for f in ("espera_min", "caminhada_min", "duracao_min"):
            row[f] = f"{row[f]:.1f}"
        row["w"] = f"{self.w:g}"
        row["lat"], row["lon"] = f"{self.lat:.7f}", f"{self.lon:.7f}"
        if self.domicilio == UBS_ID:
            row["domicilio"], row["w"], row["d"], row["P"] = "UBS", "", "", ""
        return row


def itinerary(inst: Instance, sol: Solution, start: datetime, info: dict[int, dict]) -> list[ItineraryRow]:
    """
    Paradas do roteiro em horário real, mais uma linha final de retorno à UBS.
    `info[id]` traz `lat`, `lon` e `condicao` de cada domicílio da rota e da UBS (id -1).
    """
    def at(minutes):
        return start + timedelta(minutes=float(minutes))

    rows = []
    for k, st in enumerate(sol.stops, 1):
        v = inst.visits[st.visit]
        i = info[v.id]
        rows.append(ItineraryRow(
            ordem=k, domicilio=v.id, condicao=i.get("condicao", ""), motivo=st.reason, chegada=at(st.arrival),
            inicio=at(st.start), fim=at(st.end), espera_min=st.start - st.arrival, caminhada_min=st.walk_from_prev,
            duracao_min=v.s, w=v.w, d=v.d, P=v.P, lat=i["lat"], lon=i["lon"]))
    ubs = info[UBS_ID]
    back = float(inst.t[sol.route[-2], 0])
    rows.append(ItineraryRow(
        ordem=len(rows) + 1, domicilio=UBS_ID, condicao="", motivo="retorno", chegada=at(sol.H), inicio=at(sol.H),
        fim=at(sol.H), espera_min=0.0, caminhada_min=back, duracao_min=0.0, w=0, d=0, P=0, lat=ubs["lat"], lon=ubs["lon"]))
    return rows


def route_line(G, inst: Instance, sol: Solution) -> LineString | None:
    """Trajeto completo pela malha a pé (lon, lat); None se a rota não sai do lugar."""
    nodes = [inst.visits[i].node for i in sol.route]
    coords = []
    for u, v in zip(nodes, nodes[1:]):
        if u == v:
            continue
        _, line = leg_path(G, u, v)
        seg = list(line.coords)
        coords.extend(seg if not coords else seg[1:])
    return LineString(coords) if len(coords) >= 2 else None


def route_geojson(G, inst: Instance, sol: Solution) -> dict | None:
    """Geometria GeoJSON (LineString) da rota pela malha, como guardada no Plano."""
    line = route_line(G, inst, sol)
    return mapping(line) if line is not None else None


def to_csv(rows: list[ItineraryRow]) -> str:
    """CSV (separador vírgula, decimais com ponto); grave com encoding utf-8-sig para o Excel reconhecer acentos."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(r.as_csv() for r in rows)
    return buf.getvalue()


def _describe(r: ItineraryRow) -> str:
    return (f"{r.condicao} · {r.motivo} · chegada {r.chegada:%H:%M}, atendimento {r.inicio:%H:%M}–{r.fim:%H:%M}"
            f" · w={r.w:g} d={r.d}/P={r.P}")


def to_gpx(rows: list[ItineraryRow], line: LineString | None, name: str) -> str:
    """GPX com a trilha pela malha e um waypoint por parada (01, 02, …) mais a UBS."""
    gpx = gpxpy.gpx.GPX()
    gpx.name = name
    gpx.creator = "visita-sus"
    ubs = rows[-1]
    gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(ubs.lat, ubs.lon, name="UBS", description="início e fim da jornada"))
    for r in rows[:-1]:
        gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(
            r.lat, r.lon, name=f"{r.ordem:02d} · domicílio {r.domicilio}", description=_describe(r)))
    if line is not None:
        track = gpxpy.gpx.GPXTrack(name=name)
        segment = gpxpy.gpx.GPXTrackSegment([gpxpy.gpx.GPXTrackPoint(lat, lon) for lon, lat in line.coords])
        track.segments.append(segment)
        gpx.tracks.append(track)
    return gpx.to_xml()


def to_geojson(rows: list[ItineraryRow], line: LineString | None) -> dict:
    """FeatureCollection com a rota (LineString) e as paradas (Point), para abrir em qualquer visualizador."""
    features = []
    if line is not None:
        features.append({"type": "Feature", "geometry": mapping(line), "properties": {"tipo": "rota"}})
    for r in rows:
        props = {k: v for k, v in r.as_csv().items() if k not in ("lat", "lon")}
        props["tipo"] = "ubs" if r.domicilio == UBS_ID else "parada"
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
                         "properties": props})
    return {"type": "FeatureCollection", "features": features}
