from unittest import mock

import pytest
from django.db.utils import OperationalError
from django.urls import reverse


@pytest.mark.django_db
def test_health_ok(client):
    resp = client.get(reverse("health"))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": True}


@pytest.mark.django_db
def test_health_sem_banco(client):
    with mock.patch("core.views.connection.cursor", side_effect=OperationalError):
        resp = client.get(reverse("health"))
    assert resp.status_code == 503
    assert resp.json() == {"status": "erro", "db": False}
