import importlib.metadata

_DISTRIBUTION_NAME = "rest_assured"


def get_app_version() -> str:
    try:
        return importlib.metadata.version(_DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+unknown"
