from django.test import Client, TestCase


class TemplateUrlTest(TestCase):
    def test_about(self):
        res = self.client.get("/about/")
        self.assertEqual(res.status_code, 200)

    def test_site_policy(self):
        res = self.client.get("/site-policy/")
        self.assertEqual(res.status_code, 200)

    def test_robots_txt(self):
        res = self.client.get("/site-policy/")
        self.assertEqual(res.status_code, 200)
