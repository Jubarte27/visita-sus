import csv
import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import gpxpy
import pytest

from engine import export, greedy
from engine.instance import Params
from engine.io import instance_from_files
from engine.matrix import load_graph
from tests.fixtures.mini_instance import STEP, write_mini_instance

BACKEND = Path(__file__).resolve().parents[2]
START = datetime(2026, 10, 8, 8, 0)


@pytest.fixture
def plan(tmp_path):
    files, pre = instance_from_files(write_mini_instance(tmp_path / "mini"))
    sol = greedy.solve(pre.instance, Params())
    G = load_graph(files.path / "graph.graphml")
    return files, pre.instance, sol, G


def test_itinerario(plan):
    files, inst, sol, _ = plan
    rows = export.itinerary(inst, sol, START, files.info())
    assert len(rows) == len(sol.stops) + 1
    first = rows[0]
    # urgente (4) na esquina (3,3): 6 quarteirões de 1 min a partir da UBS
    assert (first.ordem, first.domicilio, first.motivo, first.condicao) == (1, 4, "urgencia", "tuberculose")
    assert first.chegada == datetime(2026, 10, 8, 8, 6) and first.fim == datetime(2026, 10, 8, 8, 26)
    last = rows[-1]
    assert last.domicilio == export.UBS_ID and last.motivo == "retorno"
    assert (last.chegada - START).total_seconds() / 60 == pytest.approx(sol.H)


def test_csv(plan):
    files, inst, sol, _ = plan
    text = export.to_csv(export.itinerary(inst, sol, START, files.info()))
    rows = list(csv.DictReader(io.StringIO(text)))
    assert list(rows[0]) == export.CSV_FIELDS
    assert rows[0]["chegada"] == "08:06" and rows[0]["w"] == "5" and rows[0]["condicao"] == "tuberculose"
    assert rows[-1]["domicilio"] == "UBS" and rows[-1]["w"] == ""
    assert sum(float(r["caminhada_min"]) for r in rows) == pytest.approx(sol.walk)


def test_rota_pela_malha(plan):
    files, inst, sol, G = plan
    line = export.route_line(G, inst, sol)
    # na grade, cada minuto de caminhada é um quarteirão de 0,001°
    length_deg = sum(abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(line.coords, line.coords[1:]))
    assert length_deg == pytest.approx(sol.walk * STEP)
    assert line.coords[0] == line.coords[-1] == (G.nodes[inst.visits[0].node]["x"], G.nodes[inst.visits[0].node]["y"])
    geo = export.route_geojson(G, inst, sol)
    assert geo["type"] == "LineString" and len(geo["coordinates"]) == len(line.coords)


def test_gpx_e_geojson(plan):
    files, inst, sol, G = plan
    rows = export.itinerary(inst, sol, START, files.info())
    line = export.route_line(G, inst, sol)
    gpx = gpxpy.parse(export.to_gpx(rows, line, "mini"))
    assert gpx.name == "mini"
    assert [w.name for w in gpx.waypoints][:2] == ["UBS", "01 · domicílio 4"]
    assert len(gpx.waypoints) == len(sol.stops) + 1
    assert len(gpx.tracks[0].segments[0].points) == len(line.coords)
    gj = export.to_geojson(rows, line)
    kinds = [f["properties"]["tipo"] for f in gj["features"]]
    assert kinds[0] == "rota" and kinds.count("parada") == len(sol.stops) and kinds[-1] == "ubs"
    json.dumps(gj)  # serializável


def test_rota_sem_movimento(plan):
    files, inst, sol, G = plan
    sol.route = [0, 0]
    assert export.route_line(G, inst, sol) is None and export.route_geojson(G, inst, sol) is None


def test_cli_exporta_os_tres_formatos(tmp_path):
    path = write_mini_instance(tmp_path / "mini")
    out = subprocess.run([sys.executable, "-m", "engine.solve", str(path), "--metodo", "alns", "--sementes", "0",
                          "--iteracoes", "20", "--export", "csv,gpx,geojson"],
                         cwd=BACKEND, capture_output=True, text=True, check=True)
    for name in ("solucao.json", "itinerario.csv", "itinerario.gpx", "rota.geojson"):
        assert (path / name).exists(), out.stdout
    assert (path / "itinerario.csv").read_bytes().startswith(b"\xef\xbb\xbf")  # BOM para o Excel
    bad = subprocess.run([sys.executable, "-m", "engine.solve", str(path), "--export", "pdf"],
                         cwd=BACKEND, capture_output=True, text=True)
    assert bad.returncode != 0 and "pdf" in bad.stderr
