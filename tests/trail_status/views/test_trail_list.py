import re
from datetime import date, timedelta

import pytest
from django.test import TestCase
from django.urls import reverse

from trail_status.models import AreaName, StatusType

from .conftest import create_sample_condition, create_sample_data_source


class TestTrailListView(TestCase):
    def test_NO_DATA(self):
        response = self.client.get(reverse("trail_status:trail-list"))
        self.assertEqual(response.status_code, 200)


@pytest.mark.django_db
class TestTrailListViewFiltering:
    """?area= / ?source= / ?status= による絞り込みのテスト"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        source_1 = create_sample_data_source(1)
        source_2 = create_sample_data_source(2)
        self.sources = {1: source_1, 2: source_2}

        create_sample_condition(
            "A",
            data_source=source_1,
            title="A",
            area=AreaName.OKUTAMA,
            status=StatusType.CLOSURE,
            reported_at=date.today() - timedelta(days=1),
            disabled=False,
        )
        create_sample_condition(
            "B",
            data_source=source_1,
            title="B",
            area=AreaName.TANZAWA,
            status=StatusType.HAZARD,
            reported_at=date.today() - timedelta(days=2),
            disabled=False,
        )
        create_sample_condition(
            "C",
            data_source=source_2,
            title="C",
            area=AreaName.OKUTAMA,
            status=StatusType.HAZARD,
            reported_at=date.today() - timedelta(days=3),
            disabled=False,
        )
        create_sample_condition(
            "D",
            data_source=source_2,
            title="D",
            area=AreaName.TANZAWA,
            status=StatusType.CLOSURE,
            reported_at=date.today() - timedelta(days=4),
            disabled=False,
        )
        create_sample_condition(
            "E",
            data_source=source_1,
            title="E",
            area=AreaName.OKUTAMA,
            status=StatusType.CLOSURE,
            reported_at=date.today(),
            disabled=True,
        )

    @pytest.mark.parametrize(
        ("query", "expected_titles", "expected_current"),
        [
            ({}, ["A", "B", "C", "D"], {}),
            ({"area": "TANZAWA"}, ["B", "D"], {"current_area": "TANZAWA"}),
            ({"source": 2}, ["C", "D"], {"current_source": 2}),
            ({"status": "HAZARD"}, ["B", "C"], {"current_status": "HAZARD"}),
            (
                {"area": "OKUTAMA", "status": "CLOSURE"},
                ["A"],
                {"current_area": "OKUTAMA", "current_status": "CLOSURE"},
            ),
            (
                {"source": 1, "area": "TANZAWA", "status": "HAZARD"},
                ["B"],
                {"current_source": 1, "current_area": "TANZAWA", "current_status": "HAZARD"},
            ),
            ({"area": "HAKONE"}, [], {}),
            ({"area": ""}, ["A", "B", "C", "D"], {}),
        ],
        ids=[
            "4-1_絞り込みなし",
            "4-2_area",
            "4-3_source",
            "4-4_status",
            "4-5_area_status",
            "4-6_source_area_status",
            "4-7_area_データのない山域",
            "4-8_area_空の値",
        ],
    )
    def test_filtering(self, client, query, expected_titles, expected_current):
        # 情報源の番号（1 / 2）を、テストの実行時に決まる id に置き換える
        params = {key: (self.sources[value].id if key == "source" else value) for key, value in query.items()}

        response = client.get(reverse("trail_status:trail-list"), query_params=params)

        assert response.status_code == 200
        assert [c.title for c in response.context["conditions"]] == expected_titles

        for key, value in expected_current.items():
            expected = self.sources[value].id if key == "current_source" else value
            assert response.context[key] == expected

    def test_source_link_is_active(self, client):
        """サイドバーの選択中の情報源のリンクに active がつく"""
        selected, other = self.sources[2].id, self.sources[1].id

        response = client.get(reverse("trail_status:trail-list"), query_params={"source": selected})

        html = response.content.decode()
        assert re.search(rf'\?source={selected}"\s+class="sidebar-link active"', html)
        assert not re.search(rf'\?source={other}"\s+class="sidebar-link active"', html)

    @pytest.mark.parametrize("value", [" {id}", "{id_fullwidth}"], ids=["前後の空白", "全角の数字"])
    def test_source_accepts_int_convertible(self, client, value):
        """int() が受け付ける値は数値として扱う"""
        source_id = self.sources[2].id
        fullwidth = str(source_id).translate(str.maketrans("0123456789", "０１２３４５６７８９"))
        param = value.format(id=source_id, id_fullwidth=fullwidth)

        response = client.get(reverse("trail_status:trail-list"), query_params={"source": param})

        assert response.status_code == 200
        assert [c.title for c in response.context["conditions"]] == ["C", "D"]
        assert response.context["current_source"] == source_id

    def test_source_unknown_id_returns_empty(self, client):
        """存在しない id は 200 で空の一覧"""
        unknown = max(s.id for s in self.sources.values()) + 1

        response = client.get(reverse("trail_status:trail-list"), query_params={"source": unknown})

        assert response.status_code == 200
        assert list(response.context["conditions"]) == []

    def test_disallowed_host_returns_400(self, client):
        """ALLOWED_HOSTS にないホスト名は 400（400 のページの表示中にもう一度エラーにならない）"""
        response = client.get(reverse("trail_status:trail-list"), HTTP_HOST="unknown.example.com")

        assert response.status_code == 400
        assert "URLの指定が正しくありません" in response.content.decode()

    @pytest.mark.parametrize("value", ["abc", "1a", "1.5"])
    def test_source_invalid_returns_400(self, client, value):
        """数値に変換できない値は 400"""
        response = client.get(reverse("trail_status:trail-list"), query_params={"source": value})

        assert response.status_code == 400
        assert "URLの指定が正しくありません" in response.content.decode()
