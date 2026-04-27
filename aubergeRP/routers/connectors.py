from __future__ import annotations

import contextlib
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..connectors.manager import ConnectorManager
from ..models.connector import (
    ConnectorCreate,
    ConnectorInstance,
    ConnectorResponse,
    ConnectorUpdate,
)

router = APIRouter(prefix="/connectors", tags=["connectors"])


class _TestResultsStore:
    """Persistent key→bool|None store backed by a JSON sidecar file."""

    def __init__(self) -> None:
        self._data: dict[str, bool] = {}
        self._path: Path | None = None

    def _resolve_path(self) -> Path:
        from ..config import get_config
        data_dir = Path(get_config().app.data_dir)
        return data_dir / "connector_test_results.json"

    def _load(self) -> None:
        path = self._resolve_path()
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._data = {k: bool(v) for k, v in raw.items() if v is not None}
            except Exception:
                pass

    def get(self, connector_id: str, default: bool | None = None) -> bool | None:
        # Always load from disk to reflect persisted state across restarts.
        # A small cache reset on each call is acceptable at this scale.
        self._load()
        return self._data.get(connector_id, default)

    def set(self, connector_id: str, value: bool) -> None:
        self._load()
        self._data[connector_id] = value
        self._persist()

    def pop(self, connector_id: str, default: object = None) -> object:
        self._load()
        removed = self._data.pop(connector_id, default)
        self._persist()
        return removed

    def _persist(self) -> None:
        path = self._resolve_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# Module-level singleton — shared between connectors and health routers.
_last_test_results: _TestResultsStore = _TestResultsStore()


def get_connector_manager() -> ConnectorManager:
    from ..config import get_config
    config = get_config()
    return ConnectorManager(
        data_dir=config.app.data_dir,
        config=config,
    )


def _redact(instance: ConnectorInstance, is_active: bool) -> ConnectorResponse:
    """Return ConnectorResponse with api_key replaced by api_key_set bool."""
    config = dict(instance.config)
    api_key_set = bool(config.pop("api_key", ""))
    config["api_key_set"] = api_key_set
    return ConnectorResponse(
        id=instance.id,
        name=instance.name,
        type=instance.type,
        backend=instance.backend,
        is_active=is_active,
        config=config,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


def _not_found(connector_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")


# Static routes MUST be declared before parameterised ones

@router.get("/backends")
def list_backends():
    return [
        {
            "id": "openai_api",
            "name": "OpenAI-Compatible API",
            "supported_types": ["text", "image"],
            "config_schema": {
                "base_url": {"type": "string", "required": True},
                "api_key": {"type": "string", "required": False},
                "model": {"type": "string", "required": True},
            },
        }
    ]


@router.get("/")
def list_connectors(
    type: str | None = None,
    manager: ConnectorManager = Depends(get_connector_manager),
):
    instances = manager.list_connectors(type=type)
    return [_redact(i, manager.is_active(i.id)) for i in instances]


@router.post("/", status_code=201)
def create_connector(
    data: ConnectorCreate,
    manager: ConnectorManager = Depends(get_connector_manager),
):
    if data.backend not in ("openai_api",):
        raise HTTPException(status_code=400, detail=f"Unknown backend '{data.backend}'")
    instance = manager.create_connector(data)
    # Auto-activate if no active connector of this type exists yet.
    if not manager.get_active_id_for_type(instance.type):
        with contextlib.suppress(ValueError):
            manager.set_active(instance.id)
    return _redact(instance, manager.is_active(instance.id))


@router.get("/{connector_id}")
def get_connector(
    connector_id: str,
    manager: ConnectorManager = Depends(get_connector_manager),
):
    try:
        instance = manager.get_connector(connector_id)
    except KeyError:
        raise _not_found(connector_id)
    return _redact(instance, manager.is_active(connector_id))


@router.put("/{connector_id}")
def update_connector(
    connector_id: str,
    data: ConnectorUpdate,
    manager: ConnectorManager = Depends(get_connector_manager),
):
    try:
        instance = manager.update_connector(connector_id, data)
    except KeyError:
        raise _not_found(connector_id)
    return _redact(instance, manager.is_active(connector_id))


@router.delete("/{connector_id}", status_code=204)
def delete_connector(
    connector_id: str,
    manager: ConnectorManager = Depends(get_connector_manager),
):
    try:
        manager.delete_connector(connector_id)
    except KeyError:
        raise _not_found(connector_id)
    _last_test_results.pop(connector_id, None)


@router.post("/{connector_id}/test")
async def test_connector(
    connector_id: str,
    manager: ConnectorManager = Depends(get_connector_manager),
):
    try:
        result = await manager.test_connector(connector_id)
    except KeyError:
        raise _not_found(connector_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    _last_test_results.set(connector_id, result.get("connected", False))
    return result


@router.post("/{connector_id}/activate")
def activate_connector(
    connector_id: str,
    manager: ConnectorManager = Depends(get_connector_manager),
):
    try:
        manager.set_active(connector_id)
        instance = manager.get_connector(connector_id)
    except KeyError:
        raise _not_found(connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": instance.id, "type": instance.type, "is_active": True}
