def test_httpx_async_client():
    import httpx

    assert httpx.AsyncClient is not None


def test_pytest_httpx_available():
    import pytest_httpx

    assert pytest_httpx is not None
