"""
Métodos de solução por nome. Módulo leve (sem osmnx/geopandas), importado também pelos processos que
resolvem os ACS de uma equipe em paralelo.
"""

from . import alns, greedy, milp
from .instance import Instance, Params, Solution

METHODS = {"guloso": greedy.solve, "alns": alns.solve_multi_seed, "milp": milp.solve}


def run(method: str, inst: Instance, params: Params) -> Solution:
    return METHODS[method](inst, params)
