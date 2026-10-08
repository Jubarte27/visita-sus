import pytest

from engine.instance import Instance, Visit


def hand_instance() -> Instance:
    """Instância de 5 pontos de test_evaluation.py (valores conferidos à mão no docstring de lá)."""
    t = [
        [0, 5, 10, 8, 12],
        [5, 0, 4, 7, 9],
        [10, 4, 0, 6, 3],
        [8, 7, 6, 0, 5],
        [12, 9, 3, 5, 0],
    ]
    visits = [
        Visit(id=-1, node=100, s=0, w=0, P=0, d=0, tw=(0, 90)),
        Visit(id=11, node=101, s=10, w=2, P=30, d=29, tw=(0, 90)),
        Visit(id=12, node=102, s=20, w=5, P=7, d=6, tw=(0, 90), urgent=True, grave=True),
        Visit(id=13, node=103, s=15, w=1, P=60, d=65, tw=(40, 50)),
        Visit(id=14, node=104, s=30, w=4, P=15, d=2, tw=(0, 90), grave=True),
    ]
    return Instance(visits=visits, t=t, T=60, Tmax=90, K=1)


@pytest.fixture
def inst():
    return hand_instance()
