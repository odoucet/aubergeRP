"""PluginManager — discovers and manages aubergeRP plugins.

Usage (application startup)::

    from aubergeRP.plugins.manager import PluginManager

    manager = PluginManager()
    manager.discover("plugins/")   # load all plugins in a directory
    manager.load_plugin(MyPlugin)  # or register an explicit class

Then call hooks from your service code::

    manager.call_hook("on_message_received", {"conversation_id": ..., "message": ...})
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

from .base import BasePlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """Discovers, instantiates, and dispatches hooks for all registered plugins."""

    def __init__(self) -> None:
        self._plugins: list[BasePlugin] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def load_plugin(self, plugin_class: type[BasePlugin]) -> None:
        """Instantiate *plugin_class* and register it."""
        instance = plugin_class()
        self._plugins.append(instance)
        try:
            instance.on_load()
        except Exception:
            logger.exception("Plugin '%s' raised an error in on_load()", instance.name)
        logger.info("Plugin loaded: %s v%s", instance.name, instance.version)

    def unload_all(self) -> None:
        """Call on_unload() on every plugin and clear the registry."""
        for plugin in self._plugins:
            try:
                plugin.on_unload()
            except Exception:
                logger.exception("Plugin '%s' raised an error in on_unload()", plugin.name)
        self._plugins.clear()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self, directory: str | Path) -> None:
        """Load all :class:`BasePlugin` subclasses found in *directory*.

        Each ``.py`` file in *directory* (non-recursive) is imported as a
        module.  Any :class:`BasePlugin` subclass defined at module level is
        instantiated and registered.
        """
        base_dir = Path(directory)
        if not base_dir.is_dir():
            logger.debug("Plugin directory '%s' not found — skipping discovery.", base_dir)
            return

        for path in sorted(base_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            self._load_file(path)

    def _load_file(self, path: Path) -> None:
        module_name = f"_auberge_plugin_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Failed to import plugin file '%s'", path)
            return

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BasePlugin)
                and obj is not BasePlugin
            ):
                self.load_plugin(obj)

    # ------------------------------------------------------------------
    # Hook dispatch
    # ------------------------------------------------------------------

    def call_hook(self, hook_name: str, context: dict[str, Any]) -> None:
        """Call *hook_name* on every registered plugin.

        Errors in individual plugins are logged but never propagate to the
        caller.
        """
        for plugin in self._plugins:
            method = getattr(plugin, hook_name, None)
            if callable(method):
                try:
                    method(context)
                except Exception:
                    logger.exception(
                        "Plugin '%s' raised an error in hook '%s'",
                        plugin.name,
                        hook_name,
                    )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_plugins(self) -> list[dict[str, str]]:
        """Return a list of dicts describing the loaded plugins."""
        return [{"name": p.name, "version": p.version} for p in self._plugins]
