import csv
import io
from datetime import time

import gpxpy
import pytest

from core.importer import importar_instancia
from core.models import Agente, ItemRoteiro, NaoAtendida, Plano
from tests.fixtures.mini_instance import HOUSEHOLDS, write_mini_instance

pytestmark = pytest.mark.django_db
FAST = {"iterations": 30, "seeds": [0, 1]}


@pytest.fixture
def microarea(tmp_path, settings):
    settings.INSTANCES_DIR = tmp_path
    return importar_instancia(write_mini_instance(tmp_path / "mini"))[0]


def planejar(client, agente, metodo="alns", params=FAST, data="2026-10-09"):
    return client.post("/api/planos/", {"agente": agente.pk, "data": data, "metodo": metodo, "params": params},
                       content_type="application/json")


def test_microarea(client, microarea):
    r = client.get(f"/api/microareas/{microarea.pk}/")
    assert r.status_code == 200
    d = r.json()
    assert d["nome"] == "mini" and d["n_domicilios"] == len(HOUSEHOLDS)
    assert d["ubs"]["nome"] == "UBS Grade" and d["agente"]["id"] == microarea.agente.pk
    assert d["poligono"]["type"] == "Polygon"
    assert client.get("/api/microareas/999/").status_code == 404


def test_domicilios_feature_collection(client, microarea):
    r = client.get(f"/api/microareas/{microarea.pk}/domicilios/?data=2026-10-09")
    fc = r.json()
    assert fc["type"] == "FeatureCollection" and fc["data"] == "2026-10-09" and len(fc["features"]) == len(HOUSEHOLDS)
    f = next(f for f in fc["features"] if f["properties"]["codigo"] == 1)  # d=40 na data base (08/10)
    assert f["geometry"]["type"] == "Point" and len(f["geometry"]["coordinates"]) == 2
    p = f["properties"]
    assert p["dias_sem_visita"] == 41 and p["penalidade"] == pytest.approx(2 * 42 / 30)
    assert p["atrasado"] and p["atraso_dias"] == 11
    assert client.get(f"/api/microareas/{microarea.pk}/domicilios/?data=ontem").status_code == 400


def test_malha(client, microarea):
    fc = client.get(f"/api/microareas/{microarea.pk}/malha/").json()
    # grade 4×4: 24 quarteirões, cada um uma vez (sem repetir o sentido contrário)
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) == 24
    assert {f["geometry"]["type"] for f in fc["features"]} == {"LineString"}


def test_agente_patch(client, microarea):
    url = f"/api/agentes/{microarea.agente.pk}/"
    r = client.patch(url, {"hora_inicio": "07:30", "teto_graves": 1}, content_type="application/json")
    assert r.status_code == 200 and r.json()["hora_inicio"] == "07:30:00"
    assert client.patch(url, {"jornada_min": 500}, content_type="application/json").status_code == 400
    assert client.patch(url, {"velocidade_m_min": 0}, content_type="application/json").status_code == 400
    assert Agente.objects.get().teto_graves == 1


def test_planejar_e_formato(client, microarea):
    r = planejar(client, microarea.agente)
    assert r.status_code == 201, r.json()
    p = r.json()
    assert set(p) >= {"id", "agente", "microarea", "data", "metodo", "params", "metricas", "ubs", "itens",
                      "nao_atendidas", "rota", "links"}
    assert p["metodo"] == "alns" and p["status"] == "viavel" and p["params"]["seeds"] == [0, 1]
    m = p["metricas"]
    assert m["candidatas"] == len(HOUSEHOLDS) and m["visitas"] == len(p["itens"]) and m["jornada_max_min"] == 420
    assert m["visitas"] + m["nao_atendidas"] == len(HOUSEHOLDS)
    assert m["seeds_stats"]["sementes"] == [0, 1]
    primeiro = p["itens"][0]
    assert primeiro["motivo"] == "urgencia" and primeiro["condicao"] == "tuberculose"
    assert primeiro["chegada"] == "08:06" and primeiro["fim"] == "08:26"  # 6 quarteirões, 20 min de visita
    assert [i["ordem"] for i in p["itens"]] == list(range(1, len(p["itens"]) + 1))
    assert p["rota"]["type"] == "LineString" and p["rota"]["coordinates"][0] == p["rota"]["coordinates"][-1]
    assert p["links"]["csv"].endswith(f"/api/planos/{p['id']}/itinerario.csv")

    detalhe = client.get(f"/api/planos/{p['id']}/").json()
    assert detalhe["itens"] == p["itens"] and detalhe["metricas"]["objetivo"] == m["objetivo"]
    lista = client.get(f"/api/planos/?agente={microarea.agente.pk}&data=2026-10-09").json()
    assert [x["id"] for x in lista] == [p["id"]] and lista[0]["visitas"] == m["visitas"]
    assert lista[0]["nao_atendidas"] == m["nao_atendidas"]


def test_guloso_e_descartes_do_preprocessamento(client, microarea):
    # jornada máxima de 10 min: nenhum domicílio cabe sozinho (o mais perto: 1 + 15 + 1 = 17 min);
    # o plano sai vazio, com todos como inviáveis, e não como erro
    ag = microarea.agente
    ag.jornada_min, ag.jornada_max_min = 8, 10
    ag.save()
    r = planejar(client, ag, metodo="guloso", params={})
    assert r.status_code == 201
    p = r.json()
    assert p["itens"] == [] and p["status"] == "viavel"
    motivos = {n["codigo"]: n["motivo"] for n in p["nao_atendidas"]}
    assert len(motivos) == len(HOUSEHOLDS) and set(motivos.values()) == {"inviavel"}
    assert NaoAtendida.objects.filter(plano_id=p["id"]).count() == len(HOUSEHOLDS)


def test_velocidade_do_acs_reescala_os_tempos(client, microarea):
    lento = planejar(client, microarea.agente, metodo="guloso", params={}).json()
    microarea.agente.velocidade_m_min = 150
    microarea.agente.save()
    rapido = planejar(client, microarea.agente, metodo="guloso", params={}).json()
    assert rapido["itens"][0]["chegada"] == "08:03"  # metade dos 6 min
    if [i["domicilio"] for i in rapido["itens"]] == [i["domicilio"] for i in lento["itens"]]:
        assert rapido["metricas"]["caminhada_min"] == pytest.approx(lento["metricas"]["caminhada_min"] / 2)


def test_exportacoes(client, microarea):
    p = planejar(client, microarea.agente).json()
    r = client.get(f"/api/planos/{p['id']}/itinerario.csv")
    assert r.status_code == 200 and r["Content-Type"].startswith("text/csv")
    assert "attachment" in r["Content-Disposition"] and r.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert len(rows) == len(p["itens"]) + 1 and rows[-1]["domicilio"] == "UBS"
    assert rows[0]["chegada"] == p["itens"][0]["chegada"]
    assert sum(float(x["caminhada_min"]) for x in rows) == pytest.approx(p["metricas"]["caminhada_min"], abs=0.1)

    r = client.get(f"/api/planos/{p['id']}/itinerario.gpx")
    assert r.status_code == 200 and r["Content-Type"] == "application/gpx+xml"
    gpx = gpxpy.parse(r.content.decode())
    assert len(gpx.waypoints) == len(p["itens"]) + 1
    assert len(gpx.tracks[0].segments[0].points) == len(p["rota"]["coordinates"])
    assert client.get("/api/planos/999/itinerario.gpx").status_code == 404


def test_validacao(client, microarea):
    ag = microarea.agente
    assert planejar(client, ag, metodo="foo").status_code == 400
    assert planejar(client, ag, params={"zzz": 1}).status_code == 400
    assert planejar(client, ag, params={"time_limit_s": 999}).status_code == 400
    assert planejar(client, ag, params={"seeds": list(range(20))}).status_code == 400
    assert planejar(client, ag, data="09/10/2026").status_code == 400
    r = client.post("/api/planos/", {"agente": 999, "data": "2026-10-09"}, content_type="application/json")
    assert r.status_code == 400 and "agente" in r.json()
    assert Plano.objects.count() == 0


def test_instancia_sem_arquivos(client, microarea):
    (microarea.path / "graph.graphml").unlink()
    (microarea.path / "matrix.npz").unlink()
    r = planejar(client, microarea.agente)
    assert r.status_code == 409 and "indisponíveis" in r.json()["detail"]
    assert client.get(f"/api/microareas/{microarea.pk}/malha/").status_code == 409


def test_apagar_plano(client, microarea):
    p = planejar(client, microarea.agente, metodo="guloso", params={}).json()
    assert client.delete(f"/api/planos/{p['id']}/").status_code == 204
    assert Plano.objects.count() == 0 and ItemRoteiro.objects.count() == 0
    assert microarea.agente.hora_inicio == time(8, 0)


def test_comparar_metodos(client, microarea):
    p = planejar(client, microarea.agente, metodo="guloso", params={"seeds": [0], "iterations": 30}).json()
    r = client.post(f"/api/planos/{p['id']}/comparar/", {"tempo_milp": 10}, content_type="application/json")
    assert r.status_code == 200, r.json()
    d = r.json()
    assert d["candidatas"] == len(HOUSEHOLDS) and d["subinstancia"] is None
    ms = {m["metodo"]: m for m in d["metodos"]}
    assert set(ms) == {"guloso", "alns", "milp"}
    assert ms["milp"]["gap_solver"] == pytest.approx(0, abs=1e-6) and ms["milp"]["gap_para_milp"] == 0
    for m in ms.values():
        assert m["viavel"] and m["objetivo"] >= ms["milp"]["objetivo"] - 1e-6
        assert m["rota"]["type"] == "LineString" and len(m["ordem"]) == m["visitas"]
    assert ms["guloso"]["objetivo"] == pytest.approx(p["metricas"]["objetivo"])  # mesma instância do plano
    sub = client.post(f"/api/planos/{p['id']}/comparar/", {"n": 3, "seed": 1}, content_type="application/json").json()
    assert sub["candidatas"] == 3 and sub["subinstancia"] == 3
    assert client.post(f"/api/planos/{p['id']}/comparar/", {"tempo_milp": 999}, content_type="application/json").status_code == 400
    assert Plano.objects.count() == 1  # nada gravado
