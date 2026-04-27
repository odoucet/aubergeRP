"""Plugin system for aubergeRP.

Third-party plugins extend aubergeRP by subclassing :class:`BasePlugin` and
placing the module inside a directory that is registered with
:class:`PluginManager`.

Hook methods are no-ops by default so plugins only need to override the hooks
they care about.
"""

from __future__ import annotations

from typing import Any


class BasePlugin:
    """Base class for all aubergeRP plugins.

    Subclass this and override the hook methods you need.  Every hook
    receives a context dict that is passed by reference so the plugin can
    mutate it if desired (e.g., modify a message before it is sent).

    Plugin identity
    ---------------
    ``name``  — unique slug used for logging and configuration lookup.
    ``version`` — human-readable version string.
    """

    #: Unique plugin identifier.  Override in your subclass.
    name: str = "unnamed_plugin"
    #: Human-readable version.
    version: str = "0.1.0"

    # ------------------------------------------------------------------
    # Life-cycle hooks
    # ------------------------------------------------------------------

    def on_load(self) -> None:
        """Called once after the plugin is instantiated and registered."""

    def on_unload(self) -> None:
        """Called when the plugin is removed or the application shuts down."""

    # ------------------------------------------------------------------
    # Message hooks
    # ------------------------------------------------------------------

    def on_message_received(self, context: dict[str, Any]) -> None:
        """Called when the user sends a chat message.

        ``context`` keys:
          - ``conversation_id`` (str)
          - ``message`` (:class:`~aubergeRP.models.conversation.Message`)
        """

    def on_message_sent(self, context: dict[str, Any]) -> None:
        """Called after the assistant reply has been appended to the conversation.

        ``context`` keys:
          - ``conversation_id`` (str)
          - ``message`` (:class:`~aubergeRP.models.conversation.Message`)
        """

    # ------------------------------------------------------------------
    # Image hooks
    # ------------------------------------------------------------------

    def on_image_generated(self, context: dict[str, Any]) -> None:
        """Called after an image has been generated.

        ``context`` keys:
          - ``conversation_id`` (str)
          - ``prompt`` (str)
          - ``image_bytes`` (bytes)
          - ``filename`` (str)
        """

    # ------------------------------------------------------------------
    # Connector hooks
    # ------------------------------------------------------------------

    def on_connector_test(self, context: dict[str, Any]) -> None:
        """Called after a connector test completes.

        ``context`` keys:
          - ``connector_id`` (str)
          - ``connector_name`` (str)
          - ``result`` (dict with ``connected`` bool and optional ``details``)
        """
