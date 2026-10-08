"""Divisão da área de uma equipe em microáreas (engine.generator.partition_setores / partition_kmeans), sem rede."""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from engine.generator import partition_kmeans, partition_setores


def grade_de_setores(lado: int = 4, pop=None) -> gpd.GeoDataFrame:
    """lado × lado setores quadrados de 100 m (CRS métrico), população 100 cada (ou a dada)."""
    geoms = [box(c * 100, r * 100, (c + 1) * 100, (r + 1) * 100) for r in range(lado) for c in range(lado)]
    pops = pop if pop is not None else [100] * len(geoms)
    return gpd.GeoDataFrame({"CD_SETOR": [f"s{i}" for i in range(len(geoms))], "v0001": pops},
                            geometry=geoms, crs=32722, index=range(10, 10 + len(geoms)))


@pytest.mark.parametrize("n", [2, 3, 4])
def test_regioes_contiguas_e_equilibradas(n):
    setores = grade_de_setores()
    reg = partition_setores(setores, n)
    assert list(reg.index) == list(setores.index) and set(reg) == set(range(1, n + 1))
    for r in range(1, n + 1):
        uniao = setores[reg == r].union_all().buffer(0.01)
        assert uniao.geom_type == "Polygon", f"microárea {r} não é contígua"
    pops = setores.groupby(reg)["v0001"].sum()
    assert pops.max() - pops.min() <= 200  # 16 setores de 100: no máximo 2 setores de diferença


def test_populacao_desigual_equilibra_pela_populacao():
    pop = [100] * 16
    pop[0] = 1000  # um setor muito populoso fica praticamente sozinho
    setores = grade_de_setores(pop=pop)
    reg = partition_setores(setores, 2)
    pops = setores.groupby(reg)["v0001"].sum()
    assert abs(pops[1] - pops[2]) <= 200  # 2500 hab.: 1300 × 1200
    assert (reg == reg.loc[10]).sum() <= 4  # o setor de 1000 hab. fica numa região de poucos setores


def test_area_desconexa_e_poucos_setores():
    setores = grade_de_setores(lado=2)
    ilha = gpd.GeoDataFrame({"CD_SETOR": ["ilha"], "v0001": [50]}, geometry=[box(1000, 1000, 1100, 1100)], crs=32722,
                            index=[99])
    reg = partition_setores(gpd.GeoDataFrame(pd.concat([setores, ilha]), crs=32722), 2)
    assert reg.notna().all() and set(reg) == {1, 2}
    with pytest.raises(ValueError):
        partition_setores(grade_de_setores(lado=1), 2)


def test_kmeans_separa_grupos_e_e_deterministico():
    rng = np.random.default_rng(0)
    a = rng.normal((0, 0), 10, size=(30, 2))
    b = rng.normal((500, 0), 10, size=(30, 2))
    pts = np.vstack([a, b])
    lab = partition_kmeans(pts, 2, seed=0)
    assert set(lab[:30]) == {1} and set(lab[30:]) == {2}  # região 1 = a do primeiro ponto
    assert (partition_kmeans(pts, 2, seed=0) == lab).all()
