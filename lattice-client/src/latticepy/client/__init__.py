"""
latticepy.client package initializer.

This module intentionally avoids side-effects at import time (no os.environ set,
no directory creation, no sys.exit). Call `init_client_home()` from your CLI entrypoint
or application startup to create the client directory and optionally set the
LAT_CL_HOME_DIR environment variable.

This change improves testability and avoids surprising behavior when imported by other code.
"""
from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_FOLDER_NAME = ".Lattice"
DEFAULT_SUBPATH = "client"


def _detect_home_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        # Prefer USERPROFILE, fallback to expanduser
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            return Path(userprofile)
        return Path.home()
    if system in ("Linux", "Darwin"):
        return Path.home()
    # Unknown platform — return expanduser but log a warning
    logger.warning("Unsupported or unknown platform detected: %s", system)
    return Path.home()


def default_client_dir() -> Path:
    """
    Return the default client directory path (does not create it).
    If LAT_CL_HOME_DIR is set it will be returned as the path.
    """
    env = os.environ.get("LAT_CL_HOME_DIR")
    if env:
        return Path(env)
    return _detect_home_dir() / DEFAULT_FOLDER_NAME / DEFAULT_SUBPATH


def init_client_home(path: Optional[Path] = None, set_env: bool = True) -> Path:
    """
    Ensure the client home directory exists. Returns the Path used.

    - path: optional path to use; if None uses default_client_dir()
    - set_env: whether to set LAT_CL_HOME_DIR env var to the resulting path

    This DOES perform filesystem changes and should be called from the application entrypoint,
    not from import-time.
    """
    client_dir = Path(path) if path else default_client_dir()
    try:
        client_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured client directory exists: %s", client_dir)
        if set_env:
            os.environ.setdefault("LAT_CL_HOME_DIR", str(client_dir))
            logger.debug("LAT_CL_HOME_DIR set to: %s", client_dir)
    except Exception as exc:  # pragma: no cover - best-effort error handling
        logger.exception("Failed to create or initialize client dir %s: %s", client_dir, exc)
        raise
    return client_dir


__all__ = ["default_client_dir", "init_client_home"]