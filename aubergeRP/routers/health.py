from __future__ import annotations

from fastapi import APIRouter

from ..config import get_config
from ..connectors.manager import ConnectorManager
from .connectors import _last_test_results

router = APIRouter(prefix="/health", tags=["health"])

_VERSION = "0.1.0"


def _connector_info(manager: ConnectorManager, connector_id: str | None) -> dict | None:
    if not connector_id:
        return None
    try:
        instance = manager.get_connector(connector_id)
    except KeyError:
        return None
    connected = _last_test_results.get(connector_id, None)
    return {"id": instance.id, "name": instance.name, "connected": connected}


@router.get("/")
def health():
    config = get_config()
    manager = ConnectorManager(data_dir=config.app.data_dir, config=config)
    text_id = config.active_connectors.text or None
    image_id = config.active_connectors.image or None
    return {
        "status": "ok",
        "version": _VERSION,
        "connectors": {
            "text": _connector_info(manager, text_id),
            "image": _connector_info(manager, image_id),
            "video": None,
            "audio": None,
        },
    }
