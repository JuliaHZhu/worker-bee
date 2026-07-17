"""Background cron tick — extracted from agent.main to break circular deps."""
import logging
import threading

logger = logging.getLogger(__name__)

_tick_stop = threading.Event()
_tick_thread = None


def _cron_tick_loop(config: dict, skill_mgr):
    """Background thread: tick every 60 seconds."""
    from cron import scheduler
    while not _tick_stop.is_set():
        try:
            scheduler.tick(config, skill_mgr)
        except Exception as e:
            logger.info("  [Cron tick error: %s]", e)
        _tick_stop.wait(60)
