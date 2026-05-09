from django.test import TestCase
from django.urls import reverse


class TestTrailListView(TestCase):
    def test_NO_DATA(self):
        response = self.client.get(reverse("trail_status:trail-list"))
        self.assertEqual(response.status_code, 200)