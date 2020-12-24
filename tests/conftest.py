import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_coroutine(mocker, monkeypatch):
    def _create_coro_patch(*args):
        """Fixture to mock a corotine. If an object path is given, monkeypatch
        the coroutine with the mocked one.

        Args:
            args (list[str]) Arguments for monkeypatch, e.g. the object path
        """
        coro_mock = mocker.Mock()
        async def _coroutine(*args, **kwargs):
            return coro_mock(*args, **kwargs)
        if args:
            monkeypatch.setattr(*args, _coroutine)
        return _coroutine, coro_mock
    return _create_coro_patch
