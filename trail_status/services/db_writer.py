import logging
import unicodedata
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from ..models.condition import TrailCondition
from ..models.llm_usage import LlmUsage
from ..models.source import DataSource
from .llm_client import LlmConfig
from .llm_stats import LlmStats
from .pipeline import ResultSingle, SourceSchemaSingle
from .schema import TrailConditionSchemaInternal, TrailConditionSchemaList

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """全角半角・空白を揃えて比較の精度を上げる"""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip().replace(" ", "").replace("　", "")


class DbWriter:
    def __init__(self, schema_single: SourceSchemaSingle, result_by_source: ResultSingle | BaseException):
        self.schema_single = schema_single
        self.result = result_by_source

    @property
    def source_record(self) -> DataSource:
        return DataSource.objects.get(id=self.schema_single.id)

    def save_to_source(self) -> None:
        """情報源モデルへ保存"""
        source = self.source_record
        # サイト巡回日時を更新
        # ハッシュ取得andLLMスキップ時も success=True
        source.last_checked_at = timezone.now()

        # コンテンツハッシュとスクレイピング時刻を更新
        if self.result.content_changed:
            source.content_hash = self.result.new_hash
            source.last_scraped_at = timezone.now()

        # コミット
        source.save(update_fields=["content_hash", "last_scraped_at", "last_checked_at"])

    def save_condition_and_usage(self) -> dict[str, Any]:
        """登山道状況とLLM使用履歴をDBに保存"""
        # 単一ソースのAI出力を取得
        trail_conditions_list: TrailConditionSchemaList = self.result.extracted_trail_conditions

        # TrailCondition用のLLM設定(JSONField)
        ai_config = {
            k: v
            for k, v in {
                "temperature": self.result.config.temperature,
                "thinking_budget": self.result.config.thinking_budget,
            }.items()
            if v is not None
        }
        # Djangoモデル格納のため同じ形式のパイダンティックスキーマにダンプ
        internal_data_list = [
            TrailConditionSchemaInternal(**record.model_dump(), url1=self.schema_single.url1, ai_config=ai_config)
            for record in trail_conditions_list.trail_condition_records
        ]

        # DB同期とLLM使用履歴記録
        llm_stats: LlmStats = self.result.stats
        # 同期するレコードを照合
        to_update, to_create = self._reconcile_records(internal_data_list)
        # 保存
        with transaction.atomic():
            updated_count, created_count = self._save_trail_condition(to_update, to_create)
            self._save_llm_usage(llm_stats, len(internal_data_list))

        logger.info(
            f"DB保存完了: {self.schema_single.name} - {len(internal_data_list)}件 (コスト: ${llm_stats.total_fee:.4f})"
        )

        return {
            "name": self.schema_single.name,
            "count": len(internal_data_list),
            "cost": llm_stats.total_fee,
            "updated": updated_count,
            "created": created_count,
        }

    def _reconcile_records(
        self, ai_data_list: list[TrailConditionSchemaInternal]
    ) -> tuple[list[TrailCondition], list[TrailCondition]]:
        """
        AIの抽出データ(Pydantic)を既存レコードと照合する。
        所定の方法で同定し更新リストと新規作成リストをDjangoモデルで返却

        Args:
            source: データソース
            ai_data_list: AI抽出データリスト
            config: LlmConfig（AI設定情報）
            prompt_file: 使用したプロンプトファイル名
        """
        to_update: list[TrailCondition] = []
        to_create: list[TrailCondition] = []

        config: LlmConfig = self.result.config
        prompt_filename = self.source_record.prompt_filename

        for data in ai_data_list:
            # 1. AIの出力を正規化（空白や全角半角の揺れを取る）
            # これにより、AIが「雲取山 」と出しても「雲取山」として扱う
            normalized_m_name = normalize_text(data.mountain_name_raw)
            normalized_t_name = normalize_text(data.trail_name)

            # 2. 既存レコードの検索
            # ※ DB側も同様の正規化で比較したいところですが、
            #    まずは「保存されている値」を正規化したものと比較します。
            existing_record = None
            all_potential_records = TrailCondition.objects.filter(source=self.source_record, disabled=False)
            for record in all_potential_records:
                # 山名と登山道・区間名でまず同定
                if (
                    normalize_text(record.mountain_name_raw) == normalized_m_name
                    and normalize_text(record.trail_name) == normalized_t_name
                ):
                    existing_record = record
                    break

            if existing_record:
                # 2. 内容の比較（タイトル、説明、ステータスに変更があるか）
                # reported_at が今日の日付に更新されているかもチェック対象に含める
                has_changed = (
                    existing_record.title != data.title
                    or existing_record.description != data.description
                    or existing_record.status != data.status
                    or existing_record.reported_at != data.reported_at
                    or existing_record.resolved_at != data.resolved_at
                )

                if has_changed:
                    existing_record.title = data.title
                    existing_record.description = data.description
                    existing_record.status = data.status
                    existing_record.reported_at = data.reported_at
                    existing_record.resolved_at = data.resolved_at
                    # AI関連情報を更新
                    existing_record.ai_model = config.model
                    existing_record.prompt_file = prompt_filename
                    existing_record.ai_config = data.ai_config

                    to_update.append(existing_record)

                    logger.info(f"更新リストに追加: {normalized_m_name}/{normalized_t_name} (ID: {existing_record.id})")
            else:
                # 3. 新規レコードの作成
                # mountain_group は signals.py が MountainAlias に基づいて自動解決する
                # 山名原文、登山道原文は正規化する以前と以後を選択する余地のためにexculde
                generated_data_dict = data.model_dump(exclude={"mountain_name_raw", "trail_name"})
                new_record = TrailCondition(
                    source=self.source_record,
                    mountain_name_raw=data.mountain_name_raw,
                    trail_name=data.trail_name,
                    ai_model=config.model,
                    prompt_file=prompt_filename,
                    **generated_data_dict,
                )

                to_create.append(new_record)

                logger.info(f"新規作成リストに追加: {normalized_m_name}/{normalized_t_name} (ID: {new_record.id})")

        return to_update, to_create

    def _save_trail_condition(
        self, to_update: list[TrailCondition], to_create: list[TrailCondition]
    ) -> tuple[int, int]:
        """TrailConditionをDBに保存"""

        now = timezone.now()

        if to_update:
            # TrailConditionSchemaInternalのフィールド名を取得
            # Djangoモデルの更新対象フィールドと一致している前提
            fields_to_update = list(TrailConditionSchemaInternal.model_fields.keys())

            # bulk_updateではauto_now=Trueが機能しないため手動でセット
            for record in to_update:
                record.updated_at = now

            if "updated_at" not in fields_to_update:
                fields_to_update.append("updated_at")

            # 更新
            TrailCondition.objects.bulk_update(to_update, fields_to_update)
            logger.info(f"更新完了: {len(to_update)}件")

        if to_create:
            # bulk_createではauto_now_add=Trueが機能しないため手動でセット
            for record in to_create:
                record.created_at = now
                record.updated_at = now

            # 新規作成
            TrailCondition.objects.bulk_create(to_create)
            logger.info(f"新規作成完了: {len(to_create)}件")

        return len(to_update), len(to_create)

    def _save_llm_usage(self, llm_stats: LlmStats, extracted_record_count: int) -> None:
        """LLM使用履歴をDBに保存"""
        stats = llm_stats.to_dict()
        LlmUsage.objects.create(
            source=self.source_record,
            model=stats["model"],
            prompt_tokens=stats["input_tokens"],
            thinking_tokens=stats["thoughts_tokens"],
            output_tokens=stats["output_tokens"],
            cost_usd=Decimal(str(stats["total_fee"])),
            conditions_extracted=extracted_record_count,
            success=True,
            execution_time_seconds=stats.get("execution_time"),  # Noneでも可
        )
