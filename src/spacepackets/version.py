from importlib import metadata


def get_version() -> str:
    """Retrieve the package version using the
    `importlib.metadata API <https://docs.python.org/3/library/importlib.metadata.html>`_.
    """

    return metadata.version("spacepackets")
