import logging
import unicodedata
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from rapidfuzz import fuzz

from ..models.condition import TrailCondition
from ..models.llm_usage import LlmUsage
from ..models.source import DataSource
from .llm_client import LlmConfig
from .llm_stats import LlmStats
from .pipeline import ResultSingle, SourceSchemaSingle
from .schema import TrailConditionSchemaInternal, TrailConditionSchemaList

logger = logging.getLogger(__name__)


class DbWriter:
    """
    DB永続化とレコード同定を担当するクラス

    レコード同定の設定パラメータ:
    - SIMILARITY_THRESHOLD: 類似度判定の閾値（0.7推奨）
    - FIELD_WEIGHTS_*: 各フィールドの重み付け
    - BONUS_*: ボーナススコア設定
    """

    # === レコード同定アルゴリズムの設定 ===

    # 類似度判定閾値（0.0-1.0）
    # 0.8: 厳格モード（精度重視、新規作成が増える）
    # 0.7: バランスモード（推奨）
    # 0.6: 緩和モード（重複回避重視、誤同定リスク増）
    SIMILARITY_THRESHOLD = 0.7

    # フィールド重み（4フィールド使用時: description有り）
    FIELD_WEIGHT_MOUNTAIN = 0.30  # 山名
    FIELD_WEIGHT_TRAIL = 0.30     # 登山道名
    FIELD_WEIGHT_TITLE = 0.25     # タイトル
    FIELD_WEIGHT_DESC = 0.15      # 詳細説明

    # フィールド重み（3フィールド使用時: description無し）
    FIELD_WEIGHT_MOUNTAIN_NO_DESC = 0.35
    FIELD_WEIGHT_TRAIL_NO_DESC = 0.35
    FIELD_WEIGHT_TITLE_NO_DESC = 0.30

    # ボーナススコア
    BONUS_STATUS_MATCH = 0.1      # status一致時のボーナス
    BONUS_DATE_PROXIMITY = 0.05   # 日付が近い時のボーナス

    # 日付近接判定の範囲（日数）
    DATE_PROXIMITY_DAYS = 14

    # description比較時の使用文字数
    DESC_COMPARE_LENGTH = 100

    # ========================================


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
        3段階のアルゴリズムで同定を行う:
        1. 完全一致チェック（高速パス）
        2. RapidFuzzによる類似度計算（フォールバック）
        3. 新規作成

        Args:
            ai_data_list: AI抽出データリスト

        Returns:
            (更新対象レコードリスト, 新規作成レコードリスト)
        """
        to_update: list[TrailCondition] = []
        to_create: list[TrailCondition] = []

        config: LlmConfig = self.result.config
        prompt_filename = self.source_record.prompt_filename

        for new_data in ai_data_list:
            # ステップ1: 候補レコードを取得（sourceのみで絞る）
            candidates = TrailCondition.objects.filter(
                source=self.source_record,
                disabled=False,
                resolved_at__isnull=True,  # 解消済みは除外
            )

            existing_record = None

            # ステップ2: 完全一致チェック（高速パス）
            normalized_m = self.normalize_text(new_data.mountain_name_raw)
            normalized_t = self.normalize_text(new_data.trail_name)

            for candidate in candidates:
                if (
                    self.normalize_text(candidate.mountain_name_raw) == normalized_m
                    and self.normalize_text(candidate.trail_name) == normalized_t
                ):
                    existing_record: TrailCondition = candidate
                    logger.info(f"完全一致同定: {candidate.id} - {normalized_m}/{normalized_t}")
                    break

            # ステップ3: 類似度計算（フォールバック）
            if not existing_record and candidates.exists():
                scored = [(c, self._calculate_similarity(c, new_data)) for c in candidates]
                best_match, best_score = max(scored, key=lambda x: x[1])

                if best_score >= self.SIMILARITY_THRESHOLD:
                    existing_record = best_match
                    logger.info(
                        f"類似度同定: {best_match.id} - スコア {best_score:.2f} - {normalized_m}/{normalized_t}"
                    )
                else:
                    logger.info(f"類似度不足: 最高スコア {best_score:.2f} - 新規作成 - {normalized_m}/{normalized_t}")

            # ステップ4: 更新 or 新規作成
            if existing_record:
                # 内容変更チェック
                has_changed = (
                    existing_record.title != new_data.title
                    or existing_record.description != new_data.description
                    or existing_record.status != new_data.status
                    or existing_record.reported_at != new_data.reported_at
                    or existing_record.resolved_at != new_data.resolved_at
                )

                if has_changed:
                    # 更新
                    existing_record.title = new_data.title
                    existing_record.description = new_data.description
                    existing_record.status = new_data.status
                    existing_record.reported_at = new_data.reported_at
                    existing_record.resolved_at = new_data.resolved_at
                    existing_record.ai_model = config.model
                    existing_record.prompt_file = prompt_filename
                    existing_record.ai_config = new_data.ai_config

                    to_update.append(existing_record)
                    logger.info(f"更新リストに追加: {existing_record.id}")
            else:
                # 新規作成
                generated_data_dict = new_data.model_dump(exclude={"mountain_name_raw", "trail_name"})
                new_record = TrailCondition(
                    source=self.source_record,
                    mountain_name_raw=new_data.mountain_name_raw,
                    trail_name=new_data.trail_name,
                    ai_model=config.model,
                    prompt_file=prompt_filename,
                    **generated_data_dict,
                )

                to_create.append(new_record)
                logger.info(f"新規作成リストに追加: {normalized_m}/{normalized_t}")

        return to_update, to_create

    def _calculate_similarity(self, existing: TrailCondition, new_data: TrailConditionSchemaInternal) -> float:
        """
        複数フィールドを組み合わせた類似度スコア（0.0 ~ 1.0）

        Args:
            existing: 既存のDBレコード
            new_data: AIが抽出した新規データ

        Returns:
            類似度スコア（0.0 = 完全不一致、1.0 = 完全一致）
        """
        # 1. 山名の類似度（部分一致）
        mountain_score = (
            fuzz.partial_ratio(
                self.normalize_text(existing.mountain_name_raw), self.normalize_text(new_data.mountain_name_raw)
            )
            / 100.0
        )

        # 2. 登山道名の類似度（トークン順序無視）
        trail_score = (
            fuzz.token_sort_ratio(self.normalize_text(existing.trail_name), self.normalize_text(new_data.trail_name))
            / 100.0
        )

        # 3. タイトルの類似度（部分一致）
        title_score = (
            fuzz.partial_ratio(self.normalize_text(existing.title), self.normalize_text(new_data.title)) / 100.0
        )

        # 4. 詳細説明の類似度（トークンセット比較）
        if existing.description and new_data.description:
            # 両方ある場合: 4フィールド使用
            desc_score = (
                fuzz.token_set_ratio(
                    self.normalize_text(existing.description[: self.DESC_COMPARE_LENGTH]),
                    self.normalize_text(new_data.description[: self.DESC_COMPARE_LENGTH]),
                )
                / 100.0
            )

            base_score = (
                mountain_score * self.FIELD_WEIGHT_MOUNTAIN
                + trail_score * self.FIELD_WEIGHT_TRAIL
                + title_score * self.FIELD_WEIGHT_TITLE
                + desc_score * self.FIELD_WEIGHT_DESC
            )
        else:
            # descriptionがない場合: 3フィールドに重み再配分
            base_score = (
                mountain_score * self.FIELD_WEIGHT_MOUNTAIN_NO_DESC
                + trail_score * self.FIELD_WEIGHT_TRAIL_NO_DESC
                + title_score * self.FIELD_WEIGHT_TITLE_NO_DESC
            )

        # ボーナス1: statusが一致
        if existing.status == new_data.status:
            base_score = min(1.0, base_score + self.BONUS_STATUS_MATCH)

        # ボーナス2: 登録日が近い
        if new_data.reported_at and existing.created_at:
            days_diff = abs((existing.created_at.date() - new_data.reported_at).days)
            if days_diff <= self.DATE_PROXIMITY_DAYS:
                base_score = min(1.0, base_score + self.BONUS_DATE_PROXIMITY)

        return base_score

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

    @staticmethod
    def normalize_text(text: str) -> str:
        """全角半角・空白を揃えて比較の精度を上げる"""
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text).strip().replace(" ", "").replace("　", "")
