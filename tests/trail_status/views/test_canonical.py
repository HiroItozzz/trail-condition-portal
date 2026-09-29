import re

import pytest
from django.urls import reverse

from trail_status.models import AreaName, StatusType

from .conftest import create_sample_condition, create_sample_data_source


def get_canonical(html: str) -> str:
    match = re.search(r'<link rel="canonical"\s+href="([^"]*)"', html)
    assert match, "canonical の link タグがない"
    return match.group(1).strip()


@pytest.mark.django_db
class TestCanonicalUrl:
    """canonical はそのページ自身を指す（トップページに寄せない）"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.source = create_sample_data_source(1)
        self.condition = create_sample_condition(
            "A", data_source=self.source, area=AreaName.OKUTAMA, status=StatusType.CLOSURE
        )

    @pytest.mark.parametrize(
        ("url_name", "expected_path"),
        [
            ("trail_status:source-list", "/sources/"),
            ("trail_status:blog-list", "/blogs/"),
            ("about", "/about/"),
            ("site-policy", "/site-policy/"),
        ],
        ids=["情報源一覧", "ブログ集", "このサイトについて", "サイトポリシー"],
    )
    def test_default_is_own_path(self, client, url_name, expected_path):
        """canonical を上書きしないページは、そのページ自身の URL になる"""
        response = client.get(reverse(url_name))

        assert response.status_code == 200
        assert get_canonical(response.content.decode()) == f"https://trail-info.jp{expected_path}"

    def test_default_ignores_query_and_host(self, client):
        """既定の canonical はクエリパラメータとホスト名を含めない"""
        response = client.get(reverse("trail_status:source-list"), query_params={"utm_source": "x"})

        assert get_canonical(response.content.decode()) == "https://trail-info.jp/sources/"

    def test_detail(self, client):
        response = client.get(reverse("trail_status:trail-detail", args=[self.condition.id]))

        assert get_canonical(response.content.decode()) == f"https://trail-info.jp/trails/{self.condition.id}/"

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ({}, "https://trail-info.jp/"),
            ({"area": "OKUTAMA"}, "https://trail-info.jp/?area=OKUTAMA"),
            ({"source": "SOURCE_ID"}, "https://trail-info.jp/?source=SOURCE_ID"),
            ({"status": "CLOSURE"}, "https://trail-info.jp/?status=CLOSURE"),
            ({"area": "OKUTAMA", "status": "CLOSURE"}, "https://trail-info.jp/?area=OKUTAMA"),
            ({"source": "SOURCE_ID", "status": "CLOSURE"}, "https://trail-info.jp/?source=SOURCE_ID"),
        ],
        ids=["トップ", "山域", "情報源", "状況", "山域と状況", "情報源と状況"],
    )
    def test_trail_list(self, client, query, expected):
        """一覧は、山域 > 情報源 > 状況 の順に 1 つだけをクエリパラメータに残す"""
        source_id = str(self.source.id)
        params = {key: value.replace("SOURCE_ID", source_id) for key, value in query.items()}

        response = client.get(reverse("trail_status:trail-list"), query_params=params)

        assert get_canonical(response.content.decode()) == expected.replace("SOURCE_ID", source_id)
