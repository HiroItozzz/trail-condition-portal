from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from trail_status.models import AreaName, StatusType, TrailCondition
from trail_status.services.db_writer import DbWriter
from trail_status.services.pipeline import ResultSingle, SourceSchemaSingle
from trail_status.services.schema import TrailConditionSchemaInternal


@pytest.fixture
def mock_DbWriter(sample_llm_config):
    """DBライターのモック"""
    sample_source_schema = SourceSchemaSingle(
        id=100, name="sample", url1="http://url1.com", prompt_key="test_key", content_hash=None
    )
    sample_result_single = ResultSingle(success=True, message="OK", config=sample_llm_config)
    return DbWriter(sample_source_schema, sample_result_single)


@pytest.fixture
def mock_existing_record():
    """DBの登山道状況レコードのモック"""
    sample_existing_record = MagicMock(
        spec=TrailCondition,
        id=100,
        disabled=False,
        mountain_name_raw="テスト山",
        trail_name="テスト道",
        title="通行止め",
        description="テスト詳細",
        status=StatusType.CLEAR,
        resolved_at=date.today(),
        created_at=datetime.now(tz=timezone.utc) - timedelta(days=2),
    )
    return sample_existing_record


@pytest.fixture
def mock_ai_result_update():
    """更新ありモック"""
    sample_ai_result = TrailConditionSchemaInternal(
        mountain_name_raw="テスト山",
        trail_name="テスト道",
        title="通行止め",
        description="詳細：通行止め解除",
        reported_at=date.today(),
        status=StatusType.CLOSURE,  # ステータスタイプ変更で更新検知
        area=AreaName.OKUTAMA,
        url1="http://url1.com/",
        ai_config={},
    )
    return sample_ai_result


@pytest.fixture
def mock_ai_result_create():
    """新規登録モック"""
    sample_ai_result = TrailConditionSchemaInternal(
        mountain_name_raw="サンプル山",
        trail_name="サンプル道",
        title="通行止め",
        description="サンプル",
        reported_at=date.today(),
        status=StatusType.CLEAR,
        area=AreaName.OKUTAMA,
        url1="http://url1.com/",
        ai_config={},
    )
    return sample_ai_result


@pytest.fixture
def mock_ai_result_no_change():
    """更新なしモック"""
    sample_ai_result = TrailConditionSchemaInternal(
        mountain_name_raw="テスト山",
        trail_name="テスト道",
        title="通行止め",
        description="詳細",
        reported_at=date.today(),
        status=StatusType.CLEAR,
        resolved_at=date.today(),
        area=AreaName.OKUTAMA,
        url1="http://url1.com/",
        ai_config={},
    )
    return sample_ai_result


### _reconcile_records
def test_reconcile_records_update(mock_existing_record, mock_ai_result_update, mock_DbWriter):
    """データ照合ロジック AI変更検知+1件更新のテスト"""
    to_update, to_create = mock_DbWriter._reconcile_records([mock_existing_record], [mock_ai_result_update])

    # Statusが変更されているため更新1件
    assert len(to_update) == 1
    assert len(to_create) == 0


def test_reconcile_records_create(mock_existing_record, mock_ai_result_create, mock_DbWriter):
    """データ照合ロジック 新規登録のテスト"""
    to_update, to_create = mock_DbWriter._reconcile_records([mock_existing_record], [mock_ai_result_create])

    # 全く異なる出力のため新規登録1件
    assert len(to_update) == 0
    assert len(to_create) == 1


def test_reconcile_records_no_change(mock_existing_record, mock_ai_result_no_change, mock_DbWriter):
    """データ照合ロジック AI変更検知+更新なしのテスト"""
    to_update, to_create = mock_DbWriter._reconcile_records([mock_existing_record], [mock_ai_result_no_change])

    # 既存と全く同じAI出力のため更新0件+新規0件
    assert len(to_update) == 0
    assert len(to_create) == 0


def test_reconcile_records_new_source(mock_ai_result_no_change, mock_DbWriter):
    """データ照合ロジック 新規情報源のためdisabled=True"""
    to_update, to_create = mock_DbWriter._reconcile_records([], [mock_ai_result_no_change])

    # 新規情報源は人間が確認するのでdisabled=True
    assert len(to_update) == 0
    assert len(to_create) == 1
    assert to_create[0].disabled


### _calculate_simitarity
def test_calculate_similarity_same_data(mock_existing_record, mock_ai_result_no_change, mock_DbWriter):
    """類似度照合ロジック 同一データ"""
    similarity = mock_DbWriter._calculate_similarity(mock_existing_record, mock_ai_result_no_change)
    assert similarity == 1


def test_calculate_similarity_different_data(mock_existing_record, mock_ai_result_create, mock_DbWriter):
    """類似度照合ロジック 異なるデータ"""
    similarity = mock_DbWriter._calculate_similarity(mock_existing_record, mock_ai_result_create)
    print("類似度（different data）:", similarity)
    assert similarity <= 0.6


def test_calculate_similarity_similar_data(mock_existing_record, mock_ai_result_update, mock_DbWriter):
    """類似度照合ロジック 類似データ"""
    similarity = mock_DbWriter._calculate_similarity(mock_existing_record, mock_ai_result_update)
    print("類似度（similar data）:", similarity)
    assert similarity >= 0.7
