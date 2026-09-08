from __future__ import annotations

import os

from app.config import settings

# backend/ directory - used ONLY to resolve a relative DATA_DIR default.
# The data itself never lives inside the source tree.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """
    Resolves settings.data_dir to an absolute path (creating it if needed).

    business_knowledge.json, schemas.json, sql_examples.json, system_prompts.json
    and all runtime logs live under this single directory instead of inside the
    backend source tree, so they:
      - survive a `git pull` / image rebuild / redeploy (they're not part of the
        source checkout, so pulling new code never overwrites live edits made
        through the Monitor UI),
      - can be pointed at real external storage in production (e.g.
        /usr/local/aimkt/data) just by setting DATA_DIR, no code change needed.

    Defaults to "../data" relative to backend/, i.e. <repo_root>/data - a sibling
    of backend/, frontend/, monitor/.
    """
    data_dir = settings.data_dir
    if not os.path.isabs(data_dir):
        data_dir = os.path.normpath(os.path.join(_BACKEND_DIR, data_dir))
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def resolve_data_path(filename: str) -> str:
    """Resolves `filename` against the configured data directory (see get_data_dir()).
    An already-absolute path is returned unchanged."""
    if os.path.isabs(filename):
        return filename
    return os.path.join(get_data_dir(), filename)


def get_logs_dir(*subdirs: str) -> str:
    """Resolves (and creates) a logs subdirectory under the data directory,
    e.g. get_logs_dir("requests") -> <data_dir>/logs/requests."""
    path = os.path.join(get_data_dir(), "logs", *subdirs)
    os.makedirs(path, exist_ok=True)
    return path
