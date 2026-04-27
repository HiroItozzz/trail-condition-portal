from django.test import Client, TestCase
from django.urls import reverse


class TestSourceListView(TestCase):
    def test_no_sources(self):
        response = self.client.get(reverse("trail_status:source-list"))
        self.assertEqual(response.status_code, 200)