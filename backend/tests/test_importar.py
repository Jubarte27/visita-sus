import json
from datetime import date, time
from unittest import mock

import geopandas as gpd
import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse

from core.importer import ImportacaoError, importar_instancia
from core.models import Agente, Domicilio, Equipe, ItemRoteiro, Microarea, Plano, Ubs
from core.nomes import nome_ficticio
from tests.fixtures.mini_instance import HOUSEHOLDS, write_mini_instance

pytestmark = pytest.mark.django_db


@pytest.fixture
def instances(tmp_path, settings):
    settings.INSTANCES_DIR = tmp_path
    return tmp_path


def test_importa_a_instancia(instances):
    path = write_mini_instance(instances / "mini")
    m = importar_instancia(path)[0]
    assert (Ubs.objects.count(), Equipe.objects.count(), Microarea.objects.count(), Agente.objects.count()) == (1, 1, 1, 1)
    assert m.domicilios.count() == len(HOUSEHOLDS)
    assert m.instancia_dir == "mini" and m.path == path and (path / "matrix.npz").exists()
    assert str(m.equipe) == "eSF Grade" and str(m.equipe.ubs) == "UBS Grade" and str(m.agente) == nome_ficticio("mini")
    assert m.rotulo == "Microárea 01 · Grade"
    assert m.poligono["type"] == "Polygon" and m.bairros == ["Grade"] and m.area_km2 == 0.09
    assert m.ubs_node == 1
    ag = m.agente
    assert (ag.jornada_min, ag.jornada_max_min, ag.teto_graves, ag.hora_inicio) == (360, 420, 3, time(8, 0))

    d = m.domicilios.get(codigo=1)  # (0,1) hipertensão, d=40
    assert (d.condicao, d.peso, d.intervalo_max_dias, d.duracao_min) == ("hipertensao_diabetes", 2, 30, 15)
    assert d.ultima_visita == date(2026, 10, 8) - date.resolution * 40
    urg = m.domicilios.get(codigo=4)
    assert urg.urgente and urg.grave and m.domicilios.get(codigo=5).tw_inicio == 180


def test_reimportar_nao_duplica_e_atualiza(instances):
    path = write_mini_instance(instances / "mini")
    m1 = importar_instancia(path)[0]
    pks = sorted(m1.domicilios.values_list("pk", flat=True))
    m1.agente.hora_inicio = time(7, 30)
    m1.agente.save()

    visits = gpd.read_file(path / "instance.gpkg", layer="visits")
    visits.loc[1, "d"] = 3
    visits.to_file(path / "instance.gpkg", layer="visits")
    m2 = importar_instancia(path, data_base=date(2026, 10, 10))[0]

    assert m2.pk == m1.pk and Microarea.objects.count() == 1 and Agente.objects.count() == 1
    assert sorted(m2.domicilios.values_list("pk", flat=True)) == pks
    assert m2.domicilios.get(codigo=1).ultima_visita == date(2026, 10, 7)
    assert Agente.objects.get().hora_inicio == time(7, 30)  # ajuste manual preservado


def test_mesma_ubs_e_equipe_juntam_microareas(instances):
    importar_instancia(write_mini_instance(instances / "a"))
    importar_instancia(write_mini_instance(instances / "b"), agente="Maria")
    assert Ubs.objects.count() == 1 and Equipe.objects.count() == 1
    assert list(Equipe.objects.get().microareas.values_list("nome", flat=True)) == ["a", "b"]
    assert Agente.objects.get(microarea__nome="b").nome == "Maria"
    importar_instancia(write_mini_instance(instances / "c"), equipe="eSF 2", ubs_nome="UBS Central")
    assert Equipe.objects.count() == 2 and Ubs.objects.get().nome == "UBS Central"


def test_domicilios_que_sumiram(instances):
    path = write_mini_instance(instances / "mini")
    m = importar_instancia(path)[0]
    visits = gpd.read_file(path / "instance.gpkg", layer="visits")
    visits.drop(index=6).to_file(path / "instance.gpkg", layer="visits")
    importar_instancia(path)
    assert sorted(m.domicilios.values_list("codigo", flat=True)) == [1, 2, 3, 4, 5]

    plano = Plano.objects.create(agente=m.agente, data=date(2026, 10, 9), metodo="guloso", status="viavel",
                                 hora_inicio=time(8), objetivo=0, caminhada_min=0, penalidade_residual=0,
                                 excesso_min=0, retorno_min=0)
    ItemRoteiro.objects.create(plano=plano, ordem=1, domicilio=m.domicilios.get(codigo=5), chegada_min=0,
                               inicio_min=0, fim_min=10, caminhada_min=0, motivo="rotina")
    visits.drop(index=[5, 6]).to_file(path / "instance.gpkg", layer="visits")
    with pytest.raises(ImportacaoError, match="planos"):
        importar_instancia(path)
    assert m.domicilios.filter(codigo=5).exists()  # transação desfeita


def test_comando_importar(instances, capsys):
    write_mini_instance(instances / "mini")
    call_command("importar_instancia", str(instances / "mini"), "--equipe", "eSF X", "--data-base", "2026-10-09")
    assert "6 domicílios" in capsys.readouterr().out
    assert Domicilio.objects.get(codigo=1).ultima_visita == date(2026, 10, 9) - date.resolution * 40
    with pytest.raises(CommandError, match="meta.json"):
        call_command("importar_instancia", str(instances))


def test_comando_gerar_sem_rede(instances, capsys):
    def fake_generate(ubs, name, *args, **kwargs):
        path = write_mini_instance(instances / name)
        return path, json.loads((path / "meta.json").read_text())

    with mock.patch("engine.generator.generate", side_effect=fake_generate) as gen:
        call_command("gerar_instancia", "--ubs=-30.043,-51.156", "--name", "nova", "--populacao", "900")
    assert gen.call_args.args[:3] == ((-30.043, -51.156), "nova", 900)
    assert Microarea.objects.get().nome == "nova" and "6 domicílios" in capsys.readouterr().out
    with pytest.raises(CommandError, match="lat,lon"):
        call_command("gerar_instancia", "--ubs=abc", "--name", "x")


def test_admin_lista_tudo(instances, admin_client):
    importar_instancia(write_mini_instance(instances / "mini"))
    for model in ["ubs", "equipe", "microarea", "agente", "domicilio", "plano"]:
        assert admin_client.get(reverse(f"admin:core_{model}_changelist")).status_code == 200
    m = Microarea.objects.get()
    assert admin_client.get(reverse("admin:core_microarea_change", args=[m.pk])).status_code == 200


def test_importa_equipe(instances, client):
    path = write_mini_instance(instances / "eq", equipe=True)
    ms = importar_instancia(path)
    assert [m.nome for m in ms] == ["eq_1", "eq_2"]
    equipe = Equipe.objects.get()
    assert equipe.nome.startswith("eSF ") and equipe.nome.endswith(" (2 ACS)") and {m.equipe_id for m in ms} == {equipe.pk}
    nomes = [str(m.agente) for m in ms]
    assert len(set(nomes)) == 2 and not any(n.startswith("ACS ") for n in nomes)
    assert [m.rotulo.split(" · ")[0] for m in ms] == ["Microárea 01", "Microárea 02"]
    # reimportar acha a mesma equipe e mantém os nomes
    importar_instancia(path)
    assert Equipe.objects.count() == 1 and [str(m.agente) for m in Microarea.objects.order_by("nome")] == nomes
    assert sorted(ms[0].domicilios.values_list("codigo", flat=True)) == [1, 2, 5, 6]
    assert sorted(ms[1].domicilios.values_list("codigo", flat=True)) == [3, 4]
    assert all(m.instancia_dir == "eq" and m.ubs_node == 1 for m in ms)  # grafo e matriz compartilhados
    assert ms[0].poligono["type"] == "Polygon" and ms[0].poligono != ms[1].poligono
    assert ms[1].meta["microarea"]["urgentes"] == 1 and ms[0].setores == ["000000000000001"]

    # reimportar não duplica; prefixo de agente explícito
    importar_instancia(path, agente="Agente")
    assert Microarea.objects.count() == 2 and Domicilio.objects.count() == len(HOUSEHOLDS)
    assert sorted(Agente.objects.values_list("nome", flat=True)) == ["Agente 1", "Agente 2"]

    # o painel planeja os 2 ACS, cada um só com os seus domicílios
    r = client.post(f"/api/equipes/{Equipe.objects.get().pk}/planejar/",
                    {"data": "2026-10-09", "metodo": "guloso"}, content_type="application/json").json()
    assert [p["n_candidatas"] for p in r["planos"]] == [4, 2]


def test_equipe_sem_coluna_microarea(instances):
    path = write_mini_instance(instances / "eq", equipe=True)
    visits = gpd.read_file(path / "instance.gpkg", layer="visits")
    visits.drop(columns="microarea").to_file(path / "instance.gpkg", layer="visits")
    with pytest.raises(ImportacaoError, match="coluna microarea"):
        importar_instancia(path)
