"""Общие pytest-фикстуры для тестов сервисов и диспетчеров."""

import pytest

from tests.helpers import DummySession


@pytest.fixture
def dummy_session() -> DummySession:
    # Для модульных тестов достаточно лёгкого дубля сессии, который проверяет
        # оркестрацию сервисов, а не реальную интеграцию с базой данных.
    return DummySession()
