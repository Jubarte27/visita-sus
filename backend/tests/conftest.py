import pytest


@pytest.fixture(autouse=True)
def _sem_pool_de_processos(settings):
    """Os testes planejam no próprio processo; os que testam o paralelismo ligam PLANEJAMENTO_PARALELO."""
    settings.PLANEJAMENTO_PARALELO = False
