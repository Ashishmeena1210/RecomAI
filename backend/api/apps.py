import os
import sys
import threading
from django.apps import AppConfig

SKIP_COMMANDS = {"migrate", "makemigrations", "check", "test", "collectstatic", "shell"}


class ApiConfig(AppConfig):
    name = "api"

    def ready(self):
        # Opt-in warm-up: RECOMAI_PRELOAD=1 (set it for gunicorn / demos)
        if os.getenv("RECOMAI_PRELOAD", "0") != "1":
            return
        if SKIP_COMMANDS & set(sys.argv):
            return
        # runserver starts two processes; only the reloader child serves requests
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return
        from .hub_registry import get_hub
        # background thread: the server starts instantly, and early requests wait on the lock
        threading.Thread(target=get_hub, daemon=True).start()