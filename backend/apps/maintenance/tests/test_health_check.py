import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_returns_ok():
    response = APIClient().get("/health/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_check_does_not_require_authentication():
    response = APIClient().get("/health/")

    assert response.status_code == status.HTTP_200_OK
