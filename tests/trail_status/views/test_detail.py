import pytest
from django.urls import reverse

from trail_status.models import StatusType, AreaName


@pytest.mark.django_db
class TestTrailDetailView:
    def setup_method(self):
        self.params = {
            "yamareco_url": "https:// test.com/",
        }
        self.keywords_1 = {
            "https://sample1.com/",
            "テスト道1",
            "テスト山1",
            "テスト通行止め1",
            "テスト詳細説明1",
            StatusType.CLOSURE.label,
            AreaName.OKUTAMA.label,
            "https://sample1.com/ref",
            "テストコメント",
        }

    def test_detail(self, sample_condition_1, client):
        response = client.get(
            reverse("trail_status:trail-detail", kwargs={"pk": sample_condition_1.pk}), query_params=self.params
        )

        assert response.status_code == 200
        assert all(w in response.text for w in self.keywords_1)
