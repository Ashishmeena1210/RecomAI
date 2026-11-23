import logging
import os
import threading

from django.conf import settings

log = logging.getLogger(__name__)
_hub = None
_lock = threading.Lock()


def _movies(data_dir):
    from recomai.domains.movies import MovieDomain
    return MovieDomain(data_dir=data_dir)


def _books(data_dir):
    from recomai.domains.books import BookDomain
    return BookDomain(data_dir=data_dir)


def _songs(data_dir):
    from recomai.domains.songs import SongDomain
    return SongDomain(data_dir=data_dir)


FACTORIES = {"movies": _movies, "books": _books, "songs": _songs}


def build_hub():
    # Imported here so `manage.py check` / migrate don't import torch.
    from recomai.hub import RecomAIHub

    # Absolute path, so it no longer depends on the working directory.
    data_dir = str(settings.DATA_DIR)

    # The cache/ folder is still resolved relative to the CWD (I haven't seen
    # that code), so keep this until we pass cache_dir explicitly.
    os.chdir(settings.PROJECT_ROOT)

    wanted = [d.strip() for d in
          os.getenv("RECOMAI_DOMAINS", "movies,books,songs").split(",") if d.strip()]
    unknown = [d for d in wanted if d not in FACTORIES]
    if unknown:
        raise RuntimeError(f"Unknown RECOMAI_DOMAINS {unknown}. Valid: {sorted(FACTORIES)}")

    hub = RecomAIHub()
    for name in wanted:
        log.info("Loading domain '%s'...", name)
        hub.register(FACTORIES[name](data_dir))

    log.info("RecomAI hub ready: %s", hub.domains())
    return hub


def get_hub():
    """Lazy, thread-safe singleton (double-checked locking)."""
    global _hub
    if _hub is None:
        with _lock:
            if _hub is None:
                _hub = build_hub()
    return _hub