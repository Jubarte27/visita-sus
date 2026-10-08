"""
Instância mínima no formato do gerador, sem rede: grade 4×4 de ruas (1 min por quarteirão), UBS no canto
e 6 domicílios. Usada nos testes de leitura (engine.io) e de importação para o banco.

Nós da grade: id = 1 + 4·linha + coluna; coordenadas a partir de (-30.043, -51.156), 0,001° por quarteirão.
Com `equipe=True`, a instância é de uma equipe de 2 ACS (formato do gerador com --acs 2): microárea 1 = metade
oeste da grade (colunas 0–1: domicílios 1, 2, 5, 6) e microárea 2 = metade leste (domicílios 3, 4).
"""

import json
from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point, box

SIDE = 4
LAT0, LON0, STEP = -30.043, -51.156, 0.001
DATA_BASE = "2026-10-08"
BAIRRO = "Grade"


def node_id(row: int, col: int) -> int:
    return 1 + SIDE * row + col


def grid_graph(side: int = SIDE, minutes: float = 1.0) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph(crs="EPSG:4326")
    for r in range(side):
        for c in range(side):
            G.add_node(node_id(r, c), x=LON0 + c * STEP, y=LAT0 + r * STEP, street_count=4)
    for r in range(side):
        for c in range(side):
            for dr, dc in ((0, 1), (1, 0)):
                if r + dr < side and c + dc < side:
                    u, v = node_id(r, c), node_id(r + dr, c + dc)
                    for a, b in ((u, v), (v, u)):
                        G.add_edge(a, b, length=75.0, travel_time=minutes, highway="residential", oneway=False,
                                   reversed=False, osmid=1)
    return G


# (linha, coluna, condição, w, P, d, s, tw_start, tw_end, urgente, grave)
HOUSEHOLDS = [
    (0, 1, "hipertensao_diabetes", 2, 30, 40, 15, 0, 420, False, False),
    (1, 1, "idoso", 2, 30, 10, 15, 0, 180, False, False),
    (2, 2, "acamado", 4, 15, 20, 30, 0, 420, False, True),
    (3, 3, "tuberculose", 5, 7, 6, 20, 0, 420, True, True),
    (3, 0, "nenhuma", 1, 60, 5, 10, 180, 360, False, False),
    (3, 0, "gestante", 3, 30, 31, 25, 0, 420, False, False),  # mesmo ponto do anterior
]


def write_mini_instance(path: str | Path, with_data_base: bool = True, equipe: bool = False) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    G = grid_graph()
    ox.save_graphml(G, path / "graph.graphml")

    rows = [{"tipo": "ubs", "node": node_id(0, 0), "edificacao": -1, "condicao": "", "n_moradores": 0, "w": 0, "P": 0,
             "d": 0, "s": 0, "tw_start": 0, "tw_end": 420, "urgente": False, "grave": False}]
    for k, (r, c, cond, w, P, d, s, a, b, urg, grave) in enumerate(HOUSEHOLDS):
        rows.append({"tipo": "domicilio", "node": node_id(r, c), "edificacao": k, "condicao": cond, "n_moradores": 2,
                     "w": w, "P": P, "d": d, "s": s, "tw_start": a, "tw_end": b, "urgente": urg, "grave": grave})
    if equipe:
        for row, (_, c, *_resto) in zip(rows[1:], HOUSEHOLDS):
            row["microarea"] = 1 if c < 2 else 2
        rows[0]["microarea"] = 0
    geom = [Point(G.nodes[row["node"]]["x"], G.nodes[row["node"]]["y"]) for row in rows]
    visits = gpd.GeoDataFrame(rows, geometry=geom, crs=4326)
    visits["penalidade"] = [row["w"] * (row["d"] + 1) / row["P"] if row["P"] else 0.0 for row in rows]
    visits.to_file(path / "instance.gpkg", layer="visits")
    span = (SIDE - 1) * STEP
    setores = gpd.GeoDataFrame(
        {"CD_SETOR": ["000000000000001", "000000000000002"], "NM_BAIRRO": [BAIRRO, BAIRRO], "v0001": [8, 7],
         "v0007": [3, 3]},
        geometry=[box(LON0, LAT0, LON0 + span / 2, LAT0 + span), box(LON0 + span / 2, LAT0, LON0 + span, LAT0 + span)],
        crs=4326)
    setores.to_file(path / "instance.gpkg", layer="microarea")

    meta = {"nome": path.name, "seed": 0, "ubs": {"lat": LAT0, "lon": LON0},
            "microarea": {"setores": setores["CD_SETOR"].tolist(), "bairros": [BAIRRO], "moradores_censo": 15,
                          "domicilios_censo": 6, "area_km2": 0.09},
            "acs": {"jornada_min": 360, "jornada_max_min": 420, "velocidade_m_min": 75.0, "teto_graves": 3}}
    if equipe:
        meio = LON0 + span / 2
        gpd.GeoDataFrame({"microarea": [1, 2], "setores": [setores.loc[0, "CD_SETOR"], setores.loc[1, "CD_SETOR"]]},
                         geometry=[box(LON0, LAT0, meio, LAT0 + span), box(meio, LAT0, LON0 + span, LAT0 + span)],
                         crs=4326).to_file(path / "instance.gpkg", layer="microareas")
        n1 = sum(1 for h in HOUSEHOLDS if h[1] < 2)
        meta["equipe"] = {"acs": 2, "particao": "setores", "microareas": [
            {"id": 1, "setores": [setores.loc[0, "CD_SETOR"]], "bairros": [BAIRRO], "moradores_censo": 8,
             "domicilios_censo": 3, "area_km2": 0.045, "domicilios": n1, "pontos_de_acesso": 3, "urgentes": 0},
            {"id": 2, "setores": [setores.loc[1, "CD_SETOR"]], "bairros": [BAIRRO], "moradores_censo": 7,
             "domicilios_censo": 3, "area_km2": 0.045, "domicilios": len(HOUSEHOLDS) - n1, "pontos_de_acesso": 2,
             "urgentes": 1},
        ]}
    if with_data_base:
        meta["data_base"] = DATA_BASE
    (path / "meta.json").write_text(json.dumps(meta, indent=2))
    return path
