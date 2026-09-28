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
            expected = str(self.sources[value].id) if key == "current_source" else value
            assert response.context[key] == expected
