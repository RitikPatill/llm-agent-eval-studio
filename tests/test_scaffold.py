import agenteval


def test_version():
    assert agenteval.__version__ == "0.1.0"


def test_package_importable():
    # Ensures src layout is configured correctly in pyproject.toml
    import agenteval.__main__  # noqa: F401
