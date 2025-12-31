from django.apps import AppConfig


class TrailStatusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trail_status"

    def ready(self):
        import trail_status.signals

"""
**`ready()` メソッド：**
- アプリが起動したときに1回だけ実行される
- ここで `signals.py` をインポートすることで、Signalが登録される
"""