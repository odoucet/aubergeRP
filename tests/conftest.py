import pytest


@pytest.fixture(autouse=True)
def reset_config_singleton():
    from aubergeRP.config import reset_config
    from aubergeRP.database import reset_engine
    reset_config()
    reset_engine()
    yield
    reset_config()
    reset_engine()
