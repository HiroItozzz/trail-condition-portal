import pytest


@pytest.fixture(autouse=True)
def override_staticfiles(settings):
    settings.STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        }
    }
