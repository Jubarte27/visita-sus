from datetime import date, timedelta

import pytest

from engine.io import instance_from_files, load_instance_files
from engine.instance import Params
from tests.fixtures.mini_instance import HOUSEHOLDS, node_id, write_mini_instance


def test_leitura_dos_arquivos(tmp_path):
    files = load_instance_files(write_mini_instance(tmp_path / "mini"))
    assert files.data_base == date(2026, 10, 8)
    assert files.ubs_node == node_id(0, 0)
    hh = files.households()
    assert [h.id for h in hh] == list(range(1, len(HOUSEHOLDS) + 1))
    assert hh[0].ultima_visita == date(2026, 10, 8) - timedelta(days=40)
    assert hh[3].urgent and hh[3].grave and hh[4].tw == (180, 360)
    agent = files.agent()
    assert (agent.T, agent.Tmax, agent.K) == (360, 420, 3)


def test_instancia_do_dia_e_cache_da_matriz(tmp_path):
    path = write_mini_instance(tmp_path / "mini")
    files, pre = instance_from_files(path)
    assert (path / "matrix.npz").exists()
    inst = pre.instance
    assert pre.discarded == [] and len(inst.visits) == 1 + len(HOUSEHOLDS)
    assert pre.ids()[1] == 4  # a urgente vem logo após a UBS
    # tempos da grade: UBS (0,0) até a urgente (3,3) = 6 quarteirões
    assert inst.t[0, 1] == 6
    # na data base, d é o do gerador; um dia depois, todos somam 1
    assert sorted(v.d for v in inst.visits[1:]) == sorted(h[5] for h in HOUSEHOLDS)
    _, pre2 = instance_from_files(path, date(2026, 10, 9), Params(n_candidatas=2))
    assert len(pre2.instance.visits) == 1 + 1 + 2 and len(pre2.not_candidates) == 3
    assert all(v.d == HOUSEHOLDS[v.id - 1][5] + 1 for v in pre2.instance.visits[1:])


def test_meta_sem_data_base_usa_hoje(tmp_path):
    files = load_instance_files(write_mini_instance(tmp_path / "mini", with_data_base=False))
    assert files.data_base == date.today()


def test_instancia_de_equipe_por_microarea(tmp_path):
    path = write_mini_instance(tmp_path / "eq", equipe=True)
    files = load_instance_files(path)
    assert files.microareas == [1, 2]
    assert [h.id for h in files.households(1)] == [1, 2, 5, 6] and [h.id for h in files.households(2)] == [3, 4]
    assert len(files.households()) == len(HOUSEHOLDS)
    _, pre = instance_from_files(path, microarea=2)
    assert sorted(pre.ids()[1:]) == [3, 4]
    assert load_instance_files(write_mini_instance(tmp_path / "um")).microareas == []
    with pytest.raises(ValueError):
        load_instance_files(tmp_path / "um").households(1)
