import pytest

from tests.helpers import DummySession


@pytest.fixture
def dummy_session() -> DummySession:
    return DummySession()
