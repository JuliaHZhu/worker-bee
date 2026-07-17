"""Worker Bee — auto-register all tools on package import."""
import importlib
import logging
import os
import pkgutil

logger = logging.getLogger(__name__)
_load_errors = []

_tools_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
for _, _mod_name, _ in pkgutil.iter_modules([_tools_dir]):
    if not _mod_name.startswith("_"):
        try:
            importlib.import_module(f"tools.{_mod_name}")
        except Exception as e:
            logger.warning("Tool load error: %s: %s", _mod_name, e, exc_info=True)
            _load_errors.append((_mod_name, str(e)))
