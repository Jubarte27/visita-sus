import numpy as np
import pytest
from shapely.geometry import LineString

from engine.matrix import build_matrix, leg_path, load_graph, load_matrix, save_matrix, submatrix
from tests.fixtures.mini_instance import grid_graph, node_id


def test_matriz_na_grade_e_distancia_de_manhattan():
    G = grid_graph()
    cells = [(0, 0), (0, 3), (2, 1), (3, 3)]
    nodes, t = build_matrix(G, [node_id(r, c) for r, c in cells])
    expected = [[abs(r1 - r2) + abs(c1 - c2) for r2, c2 in cells] for r1, c1 in cells]
    assert nodes.tolist() == [node_id(r, c) for r, c in cells]
    assert t == pytest.approx(np.array(expected, dtype=float))


def test_nos_repetidos_e_sem_caminho():
    G = grid_graph()
    G.add_node(99, x=0.0, y=0.0)  # isolado
    nodes, t = build_matrix(G, [1, 1, 99, 2])
    assert nodes.tolist() == [1, 99, 2]
    assert t[0, 2] == 1 and t[0, 0] == 0 and t[1, 1] == 0
    assert np.isinf(t[0, 1]) and np.isinf(t[1, 2])


def test_salvar_carregar_e_recortar(tmp_path):
    nodes, t = build_matrix(grid_graph(), [1, 2, 6])
    save_matrix(tmp_path / "matrix.npz", nodes, t)
    nodes2, t2 = load_matrix(tmp_path / "matrix.npz")
    assert nodes2.tolist() == nodes.tolist() and np.array_equal(t, t2)
    sub = submatrix(nodes, t, [6, 1, 1])  # nós repetidos: domicílios no mesmo ponto
    assert sub.tolist() == [[0, 2, 2], [2, 0, 0], [2, 0, 0]]


def test_trecho_pela_malha():
    G = grid_graph()
    path, line = leg_path(G, node_id(0, 0), node_id(2, 3))
    assert len(path) == 6 and path[0] == node_id(0, 0) and path[-1] == node_id(2, 3)
    assert len(line.coords) == 6
    assert line.coords[0] == (G.nodes[path[0]]["x"], G.nodes[path[0]]["y"])
    assert leg_path(G, 1, 1) == ([1], None)


def test_trecho_com_geometria_invertida():
    G = grid_graph()
    u, v = node_id(0, 0), node_id(0, 1)
    pu, pv = (G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])
    mid = ((pu[0] + pv[0]) / 2, pu[1] + 0.0002)
    G.edges[u, v, 0]["geometry"] = LineString([pv, mid, pu])  # gravada de v para u
    _, line = leg_path(G, u, v)
    assert list(line.coords) == [pu, mid, pv]


def test_grafo_salvo_e_relido(tmp_path):
    import osmnx as ox
    ox.save_graphml(grid_graph(), tmp_path / "graph.graphml")
    G = load_graph(tmp_path / "graph.graphml")
    _, t = build_matrix(G, [node_id(0, 0), node_id(3, 3)])
    assert t[0, 1] == 6
