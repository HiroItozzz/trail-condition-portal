from django.test import TestCase
from django.urls import reverse


class TestBlogListView(TestCase):
    def test_NO_BLOGS(self):
        response = self.client.get(reverse("trail_status:blog-list"))
        self.assertEqual(response.status_code, 200)