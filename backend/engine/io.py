"""
Leitura das instâncias do gerador (backend/data/instances/<nome>/) até a Instance do dia.

  instance.gpkg  camada visits: linha 0 = UBS, demais = domicílios (id = número da linha)
  meta.json      data_base (d é contado até ela), parâmetros do ACS
  graph.graphml  malha a pé
  matrix.npz     matriz de tempos (criada aqui na primeira leitura)

Resumo de uma instância:
    .venv/bin/python -m engine.io data/instances/bomjesus [--data AAAA-MM-DD]
"""

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import numpy as np

from .instance import Params
from .matrix import build_matrix, load_graph, load_matrix, save_matrix
from .preprocess import Agent, Household, Preprocessed, preprocess


@dataclass
class InstanceFiles:
    path: Path
    meta: dict
    visits: gpd.GeoDataFrame     # em lat/lon (EPSG:4326); linha 0 = UBS
    data_base: date

    @property
    def ubs_node(self) -> int:
        return int(self.visits.loc[0, "node"])

    @property
    def microareas(self) -> list[int]:
        """Microáreas de uma instância de equipe (gerador com --acs N); [] numa instância de um ACS só."""
        return [int(m["id"]) for m in self.meta.get("equipe", {}).get("microareas", [])]

    def households(self, microarea: int | None = None) -> list[Household]:
        """Domicílios (sem a UBS), de uma microárea da equipe se `microarea`; última visita = data_base − d (D8)."""
        dom = self.visits.iloc[1:]
        if microarea is not None:
            if "microarea" not in dom.columns:
                raise ValueError(f"{self.path} não é uma instância de equipe (sem coluna microarea)")
            dom = dom[dom["microarea"] == microarea]
        return [
            Household(id=int(i), node=int(r.node), s=float(r.s), w=float(r.w), P=int(r.P),
                      ultima_visita=self.data_base - timedelta(days=int(r.d)),
                      tw=(float(r.tw_start), float(r.tw_end)), urgent=bool(r.urgente), grave=bool(r.grave))
            for i, r in dom.iterrows()
        ]

    def info(self) -> dict[int, dict]:
        """Condição e coordenadas de cada domicílio (id = linha) e da UBS (id -1), para as exportações."""
        return {(-1 if i == 0 else int(i)): {"condicao": r.condicao or "", "lat": r.geometry.y, "lon": r.geometry.x}
                for i, r in self.visits.iterrows()}

    def agent(self) -> Agent:
        acs = self.meta.get("acs", {})
        return Agent(ubs_node=self.ubs_node, T=float(acs.get("jornada_min", 360)),
                     Tmax=float(acs.get("jornada_max_min", 420)), K=int(acs.get("teto_graves", 3)))


def load_instance_files(path: str | Path) -> InstanceFiles:
    path = Path(path)
    meta = json.loads((path / "meta.json").read_text())
    visits = gpd.read_file(path / "instance.gpkg", layer="visits").to_crs(4326)
    if visits.loc[0, "tipo"] != "ubs":
        raise ValueError(f"{path}: a linha 0 de visits deveria ser a UBS")
    # instâncias anteriores ao campo data_base: d passa a ser contado até hoje
    data_base = date.fromisoformat(meta["data_base"]) if "data_base" in meta else date.today()
    return InstanceFiles(path=path, meta=meta, visits=visits, data_base=data_base)


def ensure_matrix(files: InstanceFiles) -> tuple[np.ndarray, np.ndarray]:
    """Matriz de tempos entre todos os nós de acesso da instância; calculada e salva se ainda não existir."""
    path = files.path / "matrix.npz"
    if path.exists():
        return load_matrix(path)
    nodes, t = build_matrix(load_graph(files.path / "graph.graphml"), files.visits["node"])
    save_matrix(path, nodes, t)
    return nodes, t


def instance_from_files(path: str | Path, plan_date: date | None = None, params: Params | None = None,
                        microarea: int | None = None) -> tuple[InstanceFiles, Preprocessed]:
    """Instance do dia `plan_date` (padrão: data_base da instância, ou seja, os d do gerador), de uma microárea da equipe."""
    files = load_instance_files(path)
    nodes, t = ensure_matrix(files)
    pre = preprocess(files.households(microarea), files.agent(), nodes, t, plan_date or files.data_base, params)
    return files, pre


def main():
    ap = argparse.ArgumentParser(description="Resumo de uma instância do gerador após o pré-processamento.")
    ap.add_argument("instancia", help="pasta da instância (ex.: data/instances/bomjesus)")
    ap.add_argument("--data", type=date.fromisoformat, default=None, help="data do plano (padrão: data_base)")
    ap.add_argument("--candidatas", type=int, default=Params().n_candidatas)
    ap.add_argument("--microarea", type=int, default=None, help="microárea de uma instância de equipe (1..N)")
    args = ap.parse_args()

    files, pre = instance_from_files(args.instancia, args.data, Params(n_candidatas=args.candidatas), args.microarea)
    inst = pre.instance
    nodes, t = ensure_matrix(files)
    off = ~np.eye(len(nodes), dtype=bool)
    finite = t[off & np.isfinite(t)]
    cand = [inst.visits[i] for i in inst.candidates]
    print(f"instância        {files.path.name} (data base {files.data_base}, plano {args.data or files.data_base})")
    print(f"domicílios       {len(files.visits) - 1} em {len(nodes) - 1} pontos de acesso"
          + (f" · equipe de {len(files.microareas)} microáreas; esta: {args.microarea or 'todas'}" if files.microareas else ""))
    print(f"matriz           {len(nodes)}×{len(nodes)} nós · máx {finite.max():.1f} min · média {finite.mean():.1f} min"
          f" · pares sem caminho {int((~np.isfinite(t[off])).sum())}")
    print(f"jornada          T={inst.T:.0f} Tmax={inst.Tmax:.0f} K={inst.K}")
    print(f"candidatas       {len(cand)} ({sum(v.urgent for v in cand)} urgentes, {sum(v.grave for v in cand)} graves,"
          f" {sum(v.overdue for v in cand)} atrasadas, soma das durações {sum(v.s for v in cand):.0f} min)")
    print(f"descartes        {dict(Counter(m for _, m in pre.discarded)) or 'nenhum'}")
    print(f"fora das candid. {len(pre.not_candidates)}")
    ida_volta = [inst.t[0, i] + inst.t[i, 0] for i in inst.candidates]
    print(f"UBS↔candidata    ida+volta máx {max(ida_volta):.1f} min · média {np.mean(ida_volta):.1f} min")


if __name__ == "__main__":
    main()
