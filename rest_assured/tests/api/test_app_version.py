from rest_assured.src.main import create_app
from rest_assured.src.utils.version import get_app_version


def test_app_version_matches_metadata():
    app = create_app()
    assert app.version == get_app_version()


def test_module_app_version_matches_metadata():
    from rest_assured.src.main import app
    assert app.version == get_app_version()
