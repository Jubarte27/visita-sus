import pytest

from core.importer import importar_instancia
from core.models import Equipe, Plano
from tests.fixtures.mini_instance import HOUSEHOLDS, write_mini_instance

pytestmark = pytest.mark.django_db
FAST = {"iterations": 20, "seeds": [0]}
DATA = "2026-10-09"


@pytest.fixture
def equipe(tmp_path, settings):
    settings.INSTANCES_DIR = tmp_path
    settings.PLANEJAMENTO_PARALELO = False
    importar_instancia(write_mini_instance(tmp_path / "a"))
    importar_instancia(write_mini_instance(tmp_path / "b"))
    return Equipe.objects.get()


def planejar(client, equipe, **body):
    body = {"data": DATA, "metodo": "alns", "params": FAST, **body}
    return client.post(f"/api/equipes/{equipe.pk}/planejar/", body, content_type="application/json")


def test_lista_e_detalhe(client, equipe):
    lista = client.get("/api/equipes/").json()
    assert [(e["id"], e["nome"]) for e in lista] == [(equipe.pk, "eSF Grade")]
    d = client.get(f"/api/equipes/{equipe.pk}/").json()
    assert d["ubs"]["nome"] == "UBS Grade"
    assert [m["nome"] for m in d["microareas"]] == ["a", "b"]
    assert d["microareas"][0]["n_domicilios"] == len(HOUSEHOLDS)
    assert d["microareas"][0]["agente"]["jornada_max_min"] == 420
    assert client.get("/api/equipes/999/").status_code == 404


def test_planejar_a_equipe(client, equipe):
    r = planejar(client, equipe)
    assert r.status_code == 201, r.json()
    d = r.json()
    assert d["data"] == DATA and d["metodo"] == "alns" and len(d["planos"]) == 2
    assert [p["agente"]["nome"] for p in d["planos"]] == ["ACS a", "ACS b"]
    assert Plano.objects.count() == 2
    lista = client.get(f"/api/planos/?equipe={equipe.pk}&data={DATA}").json()
    assert sorted(p["id"] for p in lista) == sorted(p["id"] for p in d["planos"])
    assert client.get(f"/api/planos/?equipe=999&data={DATA}").json() == []


def test_planejar_em_paralelo(client, equipe, settings):
    settings.PLANEJAMENTO_PARALELO = True
    paralelo = planejar(client, equipe, metodo="guloso", params={}).json()["planos"]
    settings.PLANEJAMENTO_PARALELO = False
    sequencial = planejar(client, equipe, metodo="guloso", params={}).json()["planos"]
    assert [(p["visitas"], p["objetivo"]) for p in paralelo] == [(p["visitas"], p["objetivo"]) for p in sequencial]


def test_relatorio(client, equipe):
    planejar(client, equipe, metodo="guloso", params={})
    r = client.get(f"/api/equipes/{equipe.pk}/relatorio/?data={DATA}").json()
    assert r["equipe"]["nome"] == "eSF Grade" and r["data"] == DATA and len(r["linhas"]) == 2
    a = r["linhas"][0]
    assert a["microarea"]["nome"] == "a" and not a["sem_plano"]
    assert a["candidatas"] == len(HOUSEHOLDS) and a["planejadas"] + a["nao_atendidas"] == a["candidatas"]
    assert a["domicilios"] == len(HOUSEHOLDS) and a["urgentes_fora"] == 0
    # em 09/10: atrasados (d+1 > P) são os de d = 40, 6 (P=7) e 31 (gestante), mais o de d = 20 com P = 15
    assert a["atrasados"] == 4
    tot = r["total"]
    for campo in ["planejadas", "nao_atendidas", "candidatas", "domicilios", "excesso_min", "penalidade_residual_min"]:
        assert tot[campo] == pytest.approx(sum(row[campo] for row in r["linhas"]))
    assert (tot["microareas"], tot["com_plano"], tot["sem_plano"]) == (2, 2, 0)


def test_relatorio_usa_o_ultimo_plano_e_marca_sem_plano(client, equipe):
    ag_a = equipe.microareas.get(nome="a").agente
    client.post("/api/planos/", {"agente": ag_a.pk, "data": DATA, "metodo": "guloso"}, content_type="application/json")
    ultimo = client.post("/api/planos/", {"agente": ag_a.pk, "data": DATA, "metodo": "guloso"},
                         content_type="application/json").json()
    r = client.get(f"/api/equipes/{equipe.pk}/relatorio/?data={DATA}").json()
    a, b = r["linhas"]
    assert a["plano"]["id"] == ultimo["id"]
    assert b["sem_plano"] and b["plano"] is None and not b["alerta_sobrecarga"] and b["domicilios"] == len(HOUSEHOLDS)
    assert r["total"]["sem_plano"] == 1 and r["total"]["planejadas"] == a["planejadas"]
    vazio = client.get(f"/api/equipes/{equipe.pk}/relatorio/?data=2026-12-01").json()
    assert vazio["total"]["com_plano"] == 0 and vazio["total"]["alertas"] == 0


def test_alertas(client, equipe, settings):
    planejar(client, equipe, metodo="guloso", params={})
    url = f"/api/equipes/{equipe.pk}/relatorio/?data={DATA}"
    assert client.get(url).json()["total"]["alertas"] == 0  # na grade tudo cabe, sem excesso
    settings.RELATORIO_LIMIARES = {"excesso_min": 30, "fracao_atrasados_fora": 0.0}
    a = client.get(url).json()["linhas"][0]
    assert a["alerta_sobrecarga"] == (a["atrasados_fora"] > 0)

    # urgência que não cabe na jornada: a urgente fica 6 + 20 + 6 = 32 min da UBS; com Tmax = 30 ela é inviável
    ag = equipe.microareas.get(nome="b").agente
    ag.jornada_min, ag.jornada_max_min = 25, 30
    ag.save()
    settings.RELATORIO_LIMIARES = {"excesso_min": 30, "fracao_atrasados_fora": 1.0}
    planejar(client, equipe, metodo="guloso", params={})
    b = client.get(url).json()["linhas"][1]
    assert b["urgentes_fora"] == 1 and b["alerta_sobrecarga"]
    assert any("urgência" in m for m in b["motivos_alerta"])


def test_erros(client, equipe):
    assert planejar(client, equipe, metodo="x").status_code == 400
    assert client.post(f"/api/equipes/{equipe.pk}/planejar/", {}, content_type="application/json").status_code == 400
    assert client.post("/api/equipes/999/planejar/", {"data": DATA}, content_type="application/json").status_code == 404
    m = equipe.microareas.get(nome="b")
    (m.path / "matrix.npz").unlink()
    (m.path / "graph.graphml").unlink()
    r = planejar(client, equipe)
    assert r.status_code == 409 and Plano.objects.count() == 0  # nada gravado, nem do ACS a
    assert client.get(f"/api/equipes/{equipe.pk}/relatorio/?data=ontem").status_code == 400
