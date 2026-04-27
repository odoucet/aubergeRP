"""Background scheduler for periodic media cleanup.

The scheduler runs an ``asyncio`` task in the background if enabled via
config.  It is started/stopped by ``main.py`` on app startup/shutdown.

Manual cleanup is also available through the
``POST /api/images/cleanup`` endpoint (see :mod:`aubergeRP.routers.images`).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


def cleanup_images(data_dir: str | Path, older_than_days: int) -> int:
    """Delete PNG images older than *older_than_days* days.

    Walks all sub-directories of ``{data_dir}/images/`` and removes files
    whose modification time is older than the threshold.

    Returns the number of files deleted.
    """
    import time

    base = Path(data_dir) / "images"
    if not base.exists():
        return 0

    cutoff = time.time() - older_than_days * 86400
    deleted = 0
    for img_file in base.rglob("*.png"):
        try:
            if img_file.stat().st_mtime < cutoff:
                img_file.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted


class Scheduler:
    """Simple asyncio-based background scheduler."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]

    def start(self) -> None:
        if not self._config.scheduler.enabled:
            return
        self._task = asyncio.create_task(self._run())
        logger.info(
            "Background scheduler started (interval=%ds, cleanup_older_than=%dd)",
            self._config.scheduler.interval_seconds,
            self._config.scheduler.cleanup_older_than_days,
        )

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._config.scheduler.interval_seconds)
            try:
                n = cleanup_images(
                    self._config.app.data_dir,
                    self._config.scheduler.cleanup_older_than_days,
                )
                if n:
                    logger.info("Scheduler: deleted %d old image(s)", n)
            except Exception:
                logger.exception("Scheduler: error during cleanup")
