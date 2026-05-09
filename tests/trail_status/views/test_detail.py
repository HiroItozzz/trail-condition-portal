from django.urls import reverse
import pytest


@pytest.mark.django_db
class TestTrailDetailView:
    def setup_method(self):
        self.params= {"yamareco_url": "https:// test.com/"}

    def test_detail(self, client, sample_condition):
        response = client.get(reverse("trail_status:trail-detail", kwargs={"pk": sample_condition.pk}),
                              query_params=self.params)
        assert response.status_code == 200
