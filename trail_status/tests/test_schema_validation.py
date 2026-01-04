"""
スキーマ検証のテスト
"""

import pytest

from trail_status.services.schema import TrailConditionSchemaList


def test_valid_schema_validation():
    """正常なJSONデータでのスキーマ検証"""
    valid_json = """
    {
        "trail_condition_records": [
            {
                "trail_name": "鴨沢ルート",
                "mountain_name_raw": "雲取山",
                "title": "落石注意",
                "description": "大雨の影響で落石が発生",
                "reported_at": "2025-01-02",
                "status": "HAZARD",
                "area": "OKUTAMA"
            }
        ]
    }
    """

    validated = TrailConditionSchemaList.model_validate_json(valid_json)
    assert len(validated.trail_condition_records) == 1
    assert validated.trail_condition_records[0].trail_name == "鴨沢ルート"


def test_invalid_schema_validation():
    """不正なJSONデータでのスキーマ検証"""
    invalid_json = """
    {
        "trail_condition_records": [
            {
                "trail_name": "鴨沢ルート",
                "status": "INVALID_STATUS",
                "area": "INVALID_AREA"
            }
        ]
    }
    """

    with pytest.raises(Exception):
        TrailConditionSchemaList.model_validate_json(invalid_json)


def test_empty_conditions_list():
    """空のconditionsリストでの検証"""
    empty_json = '{"trail_condition_records": []}'

    validated = TrailConditionSchemaList.model_validate_json(empty_json)
    assert len(validated.trail_condition_records) == 0
    assert isinstance(validated.trail_condition_records, list)
