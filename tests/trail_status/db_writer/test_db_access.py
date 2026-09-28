from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from trail_status.models import AreaName, DataSource, LlmUsage, OrganizationType, StatusType, TrailCondition
from trail_status.services.db_writer import DbWriter
from trail_status.services.llm_stats import LlmStats, TokenStats
from trail_status.services.prompt_utils import PromptFile
from trail_status.services.types import (
    ConditionSchemaAi,
    ConditionSchemaAiList,
    LlmModel,
    ResultSingle,
    SourceSchemaSingle,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def data_source():
    """情報源。save_to_source のテストで比較できるよう、ハッシュと日時を古い値にしておく"""
    old_time = timezone.now() - timedelta(days=2)
    return DataSource.objects.create(
        name="テスト機関",
        organization_type=OrganizationType.MUNICIPALITY,
        prefecture_code=13,
        prompt_key="test_org",
        url1="https://sample.com/",
        url2="https://sample.com/data/",
        description="サンプル詳細説明",
        data_format="WEB",
        area_name=AreaName.OKUTAMA,
        content_hash="old",
        last_scraped_at=old_time,
        last_checked_at=old_time,
    )


@pytest.fixture
def source_schema(data_source):
    return SourceSchemaSingle(
        id=data_source.id,
        name=data_source.name,
        url1=data_source.url1,
        prompt_file=PromptFile(prompt="test"),
        content_hash=data_source.content_hash,
    )


@pytest.fixture
def token_stats():
    return TokenStats(
        input_tokens=1000,
        thoughts_tokens=200,
        pure_output_tokens=300,
        input_letter_count=500,
        output_letter_count=100,
        model=LlmModel.GEMINI_2_5_FLASH,
    )


class TestSaveToSource:
    def test_content_changed(self, data_source, source_schema):
        """内容が変わったとき、ハッシュと2つの日時がすべて更新される"""
        original_scraped_at = data_source.last_scraped_at
        original_checked_at = data_source.last_checked_at

        result = ResultSingle(success=True, message="OK", content_changed=True, new_hash="new")
        DbWriter(source_schema, result).save_to_source()

        data_source.refresh_from_db()
        assert data_source.content_hash == "new"
        assert data_source.last_scraped_at > original_scraped_at
        assert data_source.last_checked_at > original_checked_at

    def test_content_not_changed(self, data_source, source_schema):
        """内容が変わらないとき、ハッシュとスクレイピング日時はそのまま、巡回日時だけ更新される"""
        original_scraped_at = data_source.last_scraped_at
        original_checked_at = data_source.last_checked_at

        result = ResultSingle(success=True, message="OK", content_changed=False, new_hash="old")
        DbWriter(source_schema, result).save_to_source()

        data_source.refresh_from_db()
        assert data_source.content_hash == "old"
        assert data_source.last_scraped_at == original_scraped_at
        assert data_source.last_checked_at > original_checked_at

    def test_result_is_exception(self, data_source, source_schema):
        """結果が例外のとき、情報源は一切更新されない"""
        original_content_hash = data_source.content_hash
        original_scraped_at = data_source.last_scraped_at
        original_checked_at = data_source.last_checked_at

        DbWriter(source_schema, RuntimeError("失敗")).save_to_source()

        data_source.refresh_from_db()
        assert data_source.content_hash == original_content_hash
        assert data_source.last_scraped_at == original_scraped_at
        assert data_source.last_checked_at == original_checked_at


class TestPersistConditionAndUsage:
    def test_first_sync_creates_records(self, data_source, source_schema, token_stats, llm_config_factory):
        """情報源が初回で TrailCondition が1件もないとき、全件が disabled=True で新規作成される"""
        records = [
            ConditionSchemaAi(trail_name="道1", title="タイトル1", status=StatusType.CLOSURE, area=AreaName.OKUTAMA),
            ConditionSchemaAi(trail_name="道2", title="タイトル2", status=StatusType.HAZARD, area=AreaName.OKUTAMA),
        ]
        config = llm_config_factory(LlmModel.GEMINI_2_5_FLASH)
        stats = LlmStats(token_stats)
        result = ResultSingle(
            success=True,
            message="OK",
            extracted_trail_conditions=ConditionSchemaAiList(trail_condition_records=records),
            stats=stats,
            config=config,
        )

        ret = DbWriter(source_schema, result).persist_condition_and_usage()

        conditions = list(TrailCondition.objects.filter(source=data_source))
        assert len(conditions) == 2
        for condition in conditions:
            assert condition.disabled is True
            assert condition.created_at is not None
            assert condition.updated_at is not None
            assert condition.synced_at is not None
            assert condition.ai_model == config.model
            assert condition.prompt_file == config.prompt_filename

        usages = list(LlmUsage.objects.filter(source=data_source))
        assert len(usages) == 1
        usage = usages[0]
        assert usage.prompt_tokens == token_stats.input_tokens
        assert usage.conditions_extracted == 2
        assert usage.success is True
        assert usage.cost_usd == Decimal(str(stats.total_fee))

        assert ret["count"] == 2
        assert ret["created"] == 2
        assert ret["updated"] == 0

    def test_existing_record_is_updated(self, data_source, source_schema, token_stats, llm_config_factory):
        """山名・登山道名・タイトル・説明が同じで status だけ変わったとき、既存レコードが更新される"""
        existing = TrailCondition.objects.create(
            source=data_source,
            url1=data_source.url1,
            trail_name="道1",
            mountain_name_raw="山1",
            title="タイトル1",
            description="説明1",
            status=StatusType.CLEAR,
            area=AreaName.OKUTAMA,
            ai_model="",
            prompt_file="",
            ai_config={},
            disabled=False,
        )
        original_updated_at = existing.updated_at

        records = [
            ConditionSchemaAi(
                trail_name="道1",
                mountain_name_raw="山1",
                title="タイトル1",
                description="説明1",
                status=StatusType.CLOSURE,
                area=AreaName.OKUTAMA,
            ),
        ]
        config = llm_config_factory(LlmModel.GEMINI_2_5_FLASH)
        stats = LlmStats(token_stats)
        result = ResultSingle(
            success=True,
            message="OK",
            extracted_trail_conditions=ConditionSchemaAiList(trail_condition_records=records),
            stats=stats,
            config=config,
        )

        ret = DbWriter(source_schema, result).persist_condition_and_usage()

        assert TrailCondition.objects.filter(source=data_source).count() == 1
        existing.refresh_from_db()
        assert existing.status == StatusType.CLOSURE
        assert existing.updated_at > original_updated_at

        assert ret["updated"] == 1
        assert ret["created"] == 0

    def test_failure_rolls_back_everything(
        self, data_source, source_schema, token_stats, llm_config_factory, monkeypatch
    ):
        """LLM使用履歴の保存で失敗したら、TrailCondition の保存も取り消される"""

        def _raise_runtime_error(self, llm_stats, extracted_record_count):
            raise RuntimeError("失敗")

        monkeypatch.setattr(DbWriter, "_commit_llm_usage", _raise_runtime_error)

        records = [
            ConditionSchemaAi(trail_name="道1", title="タイトル1", status=StatusType.CLOSURE, area=AreaName.OKUTAMA),
            ConditionSchemaAi(trail_name="道2", title="タイトル2", status=StatusType.HAZARD, area=AreaName.OKUTAMA),
        ]
        config = llm_config_factory(LlmModel.GEMINI_2_5_FLASH)
        stats = LlmStats(token_stats)
        result = ResultSingle(
            success=True,
            message="OK",
            extracted_trail_conditions=ConditionSchemaAiList(trail_condition_records=records),
            stats=stats,
            config=config,
        )

        with pytest.raises(RuntimeError):
            DbWriter(source_schema, result).persist_condition_and_usage()

        assert TrailCondition.objects.filter(source=data_source).count() == 0
        assert LlmUsage.objects.filter(source=data_source).count() == 0
