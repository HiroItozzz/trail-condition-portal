import pytest
from django.urls import reverse

from trail_status.models import AreaName


@pytest.mark.django_db
class TestSourceListView:
    def setup_method(self):
        self.keywords_1 = {
            "テスト機関1",
            "https://sample1.com/",
            "https://sample1.com/data/",
            AreaName.OKUTAMA.label,
            # "サンプル詳細説明1",
        }

    def test_NO_SOURCES(self, client):
        response = client.get("/sources/")
        assert response.templates[0].name == "trail_status/sources.html"
        assert response.status_code == 200

    def test_ONE_SOURCE(self, sample_data_source_1, client):
        response = client.get(reverse("trail_status:source-list"))
        assert response.status_code == 200
        assert all(w in response.text for w in self.keywords_1)
