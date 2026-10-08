"""
Matriz de tempos a pé (módulo M2 da proposta).

Tempo entre dois pontos = caminho mínimo na malha a pé (Dijkstra) com peso `travel_time` (min, gravado
pelo gerador em cada aresta). A matriz é calculada uma vez por instância, entre todos os nós de acesso
(UBS + domicílios), e salva em `matrix.npz`; o trajeto de cada trecho só é recalculado para desenhar a
rota e gerar o GPX (`leg_path`).
"""

from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
from shapely.geometry import LineString

WEIGHT = "travel_time"
# atributos que o osmnx tentaria converter para bool/int, mas podem vir como listas do OSM
EDGE_DTYPES = {"oneway": str, "reversed": str, "bridge": str, "tunnel": str, "junction": str, WEIGHT: float}


def load_graph(path: str | Path) -> nx.MultiDiGraph:
    """Malha a pé salva pelo gerador (lat/lon; arestas com length em m e travel_time em min)."""
    return ox.load_graphml(path, edge_dtypes=EDGE_DTYPES)


def build_matrix(G: nx.MultiDiGraph, nodes) -> tuple[np.ndarray, np.ndarray]:
    """
    Tempos a pé entre todos os pares de `nodes` (repetidos são ignorados). Devolve (nós, t) com
    t[i, j] = tempo de nós[i] até nós[j] em minutos; pares sem caminho ficam com inf.
    """
    nodes = np.array(list(dict.fromkeys(int(n) for n in nodes)), dtype=np.int64)
    pos = {n: i for i, n in enumerate(nodes)}
    t = np.full((len(nodes), len(nodes)), np.inf)
    for i, source in enumerate(nodes):
        for target, dist in nx.single_source_dijkstra_path_length(G, int(source), weight=WEIGHT).items():
            j = pos.get(target)
            if j is not None:
                t[i, j] = dist
    return nodes, t


def save_matrix(path: str | Path, nodes: np.ndarray, t: np.ndarray) -> None:
    np.savez_compressed(path, nodes=nodes, t=t)


def load_matrix(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path) as f:
        return f["nodes"], f["t"]


def submatrix(nodes: np.ndarray, t: np.ndarray, wanted) -> np.ndarray:
    """Recorta a matriz para a sequência de nós `wanted` (pode repetir nós: domicílios no mesmo ponto)."""
    pos = {int(n): i for i, n in enumerate(nodes)}
    idx = np.array([pos[int(n)] for n in wanted], dtype=np.int64)
    return t[np.ix_(idx, idx)]


def _edge_coords(G, u, v) -> list[tuple[float, float]]:
    """Coordenadas (lon, lat) da aresta u→v mais rápida, orientadas de u para v."""
    data = min(G.get_edge_data(u, v).values(), key=lambda d: d.get(WEIGHT, np.inf))
    pu, pv = (G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])
    geom = data.get("geometry")
    if geom is None:
        return [pu, pv]
    coords = list(geom.coords)
    # geometria gravada no sentido contrário: inverte para começar em u
    if np.hypot(coords[0][0] - pu[0], coords[0][1] - pu[1]) > np.hypot(coords[-1][0] - pu[0], coords[-1][1] - pu[1]):
        coords.reverse()
    return coords


def leg_path(G: nx.MultiDiGraph, u: int, v: int) -> tuple[list[int], LineString | None]:
    """Caminho mais rápido de u até v: (nós, geometria pela malha). Trecho nulo (u == v) não tem geometria."""
    path = nx.shortest_path(G, u, v, weight=WEIGHT)
    if len(path) < 2:
        return path, None
    coords = []
    for a, b in zip(path, path[1:]):
        seg = _edge_coords(G, a, b)
        coords.extend(seg if not coords else seg[1:])
    return path, LineString(coords)
