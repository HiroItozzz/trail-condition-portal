import os
import sys

from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "scheduler"

    def ready(self):
        ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "False").lower() == "true"

        # runserverなどで2回起動されるのを防ぐ（または特定のプロセスのみで起動）
        if ENABLE_SCHEDULER and "runserver" in sys.argv:
            from . import scheduler
            scheduler.start()
