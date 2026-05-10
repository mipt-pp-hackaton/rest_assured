import importlib.metadata

from rest_assured.src.utils.version import get_app_version


def test_get_app_version_string():
    v = get_app_version()
    assert isinstance(v, str)
    assert len(v) > 0
    try:
        expected = importlib.metadata.version("rest_assured")
        assert v == expected
    except importlib.metadata.PackageNotFoundError:
        assert "unknown" in v or v == "0.0.0+unknown"
