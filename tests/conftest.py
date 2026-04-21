import pytest


@pytest.fixture(autouse=True)
def reset_config_singleton():
    from aubergeRP.config import reset_config
    reset_config()
    yield
    reset_config()
