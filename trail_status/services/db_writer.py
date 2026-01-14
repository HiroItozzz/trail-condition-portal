import logging
import unicodedata
from decimal import Decimal
from functools import lru_cache
from typing import Any

from django.db import transaction
from django.utils import timezone
from rapidfuzz import fuzz
from sudachipy import Dictionary, SplitMode

from config.settings import DEBUG

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
    FIELD_WEIGHT_MOUNTAIN = 0.2  # 山名
    FIELD_WEIGHT_TRAIL = 0.3  # 登山道名
    FIELD_WEIGHT_TITLE = 0.1  # タイトル
    FIELD_WEIGHT_DESC = 0.4  # 詳細説明

    # フィールド重み（3フィールド使用時: description無し）
    FIELD_WEIGHT_MOUNTAIN_NO_DESC = 0.2
    FIELD_WEIGHT_TRAIL_NO_DESC = 0.4
    FIELD_WEIGHT_TITLE_NO_DESC = 0.4

    # ボーナススコア
    BONUS_STATUS_MATCH = 0  # status一致時のボーナス
    BONUS_DATE_PROXIMITY = 0  # 日付が近い時のボーナス

    # 日付近接判定の範囲（日数）
    DATE_PROXIMITY_DAYS = 14

    # description比較時の使用文字数
    DESC_COMPARE_LENGTH = 200

    # sudachipyのトークン分割モード (A | B | C)
    SPLIT_MODE = SplitMode.C

    # ========================================

    # 形態素解析器の初期化
    sudachi = Dictionary(dict="core").create()

    def __init__(
        self,
        source_schema_single: SourceSchemaSingle,
        result_by_source: ResultSingle | BaseException,
        on_duplicate_warning=None,
    ):
        self.source_schema_single = source_schema_single
        self.result = result_by_source
        self.on_duplicate_warning = on_duplicate_warning  # コールバック関数

    @property
    def source_record(self) -> DataSource:
        return DataSource.objects.get(id=self.source_schema_single.id)

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

    def persist_condition_and_usage(self) -> dict[str, Any]:
        """登山道状況とLLM使用履歴をDBに保存"""

        internal_data_list = self._convert_to_internal_schema()

        # DB同期とLLM使用履歴記録
        llm_stats: LlmStats = self.result.stats
        # 同期するレコードを照合
        to_update, to_create, duplicate_warnings = self.reconcile_records(internal_data_list)

        # 重複警告があればログ出力
        if duplicate_warnings:
            logger.warning(f"重複照合警告が {len(duplicate_warnings)}件 発生しました")

        # 保存
        with transaction.atomic():
            updated_count, created_count = self._commit_trail_condition(to_update, to_create)
            self._commit_llm_usage(llm_stats, len(internal_data_list))

        logger.info(
            f"DB保存完了: {self.source_schema_single.name} - {len(internal_data_list)}件 (コスト: ${llm_stats.total_fee:.4f})"
        )

        return {
            "name": self.source_schema_single.name,
            "count": len(internal_data_list),
            "cost": llm_stats.total_fee,
            "updated": updated_count,
            "created": created_count,
        }

    def _convert_to_internal_schema(self):
        """AI出力結果とAI設定を保存用スキーマへ統合"""
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
            TrailConditionSchemaInternal(
                **record.model_dump(),
                url1=self.source_schema_single.url1,
                ai_config=ai_config,
                ai_model=self.result.config.model,
                prompt_file=self.source_record.prompt_filename,
            )
            for record in trail_conditions_list.trail_condition_records
        ]
        return internal_data_list

    def _commit_trail_condition(
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

    def _commit_llm_usage(self, llm_stats: LlmStats, extracted_record_count: int) -> None:
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

    def reconcile_records(
        self, ai_record_list: list[TrailConditionSchemaInternal]
    ) -> tuple[list[TrailCondition], list[TrailCondition], list[dict]]:
        """
        AIの抽出データ(Pydantic)を既存レコードと照合する。
        3段階のアルゴリズムで同定を行う:
        1. 完全一致チェック（高速パス）
        2. RapidFuzzによる類似度計算（フォールバック）
        3. 新規作成

        Args:
            ai_data_list: AI抽出データリスト

        Returns:
            (更新対象レコードリスト, 新規作成レコードリスト, 重複警告リスト)
        """
        to_update: list[TrailCondition] = []
        to_create: list[TrailCondition] = []
        duplicate_warnings: list[dict] = []  # 重複警告情報

        logger.info(f"\n--- データ照合開始: {self.source_record.name}")
        matches = []
        # ステップ1: 候補レコードを取得（sourceのみで絞る）
        candidates = list(
            TrailCondition.objects.filter(
                source=self.source_record,
                disabled=False,
            )
        )

        # ステップ2: 候補レコード×AI出力レコードを総当りで類似度計算
        for ai_idx, ai_record in enumerate(ai_record_list):
            for candidate in candidates:
                score = self._calculate_similarity(candidate, ai_record)
                if score >= self.SIMILARITY_THRESHOLD:
                    matches.append((score, candidate, ai_idx))

        # 類似度順にソート
        matches.sort(key=lambda x: x[0], reverse=True)

        used_model_records = set()
        used_ai_records = set()
        for score, db_record, ai_idx in matches:
            if db_record.id in used_model_records or ai_idx in used_ai_records:
                continue

            # ピックアップ済みのDB,AI出力をそれぞれ登録
            used_model_records.add(db_record.id)
            used_ai_records.add(ai_idx)

            matched_ai_record: TrailConditionSchemaInternal = ai_record_list[ai_idx]

            matched_m_name = matched_ai_record.mountain_name_raw
            matched_t_name = matched_ai_record.trail_name
            logger.info(f"類似度同定 - AI出力: {matched_m_name}/{matched_t_name}")
            logger.info(
                f"スコア: {score:.2f} - DB_ID: {db_record.id} / {db_record.mountain_name_raw}/{db_record.trail_name} "
            )

            # 内容変更チェック
            has_changed = (
                db_record.title != matched_ai_record.title
                or db_record.description != matched_ai_record.description
                or db_record.status != matched_ai_record.status
                or db_record.reported_at != matched_ai_record.reported_at
                or db_record.resolved_at != matched_ai_record.resolved_at
            )

            if has_changed:
                # 更新
                db_record.title = matched_ai_record.title
                db_record.description = matched_ai_record.description
                db_record.status = matched_ai_record.status
                db_record.reported_at = matched_ai_record.reported_at
                db_record.resolved_at = matched_ai_record.resolved_at
                db_record.ai_model = matched_ai_record.ai_model
                db_record.prompt_file = matched_ai_record.prompt_file
                db_record.ai_config = matched_ai_record.ai_config

                to_update.append(db_record)
                logger.info("==> 変更あり/更新リストに追加")

        for ai_idx, ai_record in enumerate(ai_record_list):
            if ai_idx in used_ai_records:
                # すでにピックアップされていたらスキップ
                continue

            # 新規作成
            generated_record_dict = ai_record.model_dump(exclude={"mountain_name_raw", "trail_name"})
            new_record = TrailCondition(
                source=self.source_record,
                mountain_name_raw=ai_record.mountain_name_raw,
                trail_name=ai_record.trail_name,
                **generated_record_dict,
            )

            to_create.append(new_record)
            logger.info(f"新規作成リストに追加 - AI出力名: {ai_record.mountain_name_raw}/{ai_record.trail_name}")
            if DEBUG:
                for loser_score, loser_db_record, loser_idx in matches:
                    if ai_idx == loser_idx:
                        d_i = loser_db_record.id
                        d_m = loser_db_record.mountain_name_raw
                        d_t = loser_db_record.trail_name
                        logger.info(f"最高スコア: {loser_score:.2f} - 対象既存レコード: {d_i} / {d_m}/{d_t}")
                        break
                else:
                    logger.info(f"所定の閾値{self.SIMILARITY_THRESHOLD}を超えるレコードは見つかりません")

        logger.info(f"--- データ照合終了: {self.source_record.name}")
        return to_update, to_create, duplicate_warnings

    def _calculate_similarity(self, existing: TrailCondition, new_data: TrailConditionSchemaInternal) -> float:
        """
        複数フィールドを組み合わせた類似度スコア（0.0 ~ 1.0）

        Args:
            existing: 既存のDBレコード
            new_data: AIが抽出した新規データ

        Returns:
            類似度スコア（0.0 = 完全不一致、1.0 = 完全一致）
        """
        # 1. 山名の類似度
        mountain_score = (
            fuzz.token_set_ratio(
                existing.mountain_name_raw,
                new_data.mountain_name_raw,
                processor=lambda s: self.decompose_text(s, noun_only=True),
                score_cutoff=0.6,
            )
            / 100.0
        )

        # 2. 登山道名の類似度
        trail_score = (
            fuzz.WRatio(
                existing.trail_name,
                new_data.trail_name,
                processor=lambda s: self.decompose_text(s, noun_only=False),
                score_cutoff=0.5,
            )
            / 100.0
        )

        # 3. タイトルの類似度
        title_score = (
            fuzz.WRatio(
                existing.title,
                new_data.title,
                processor=lambda s: self.decompose_text(s, noun_only=False),
                score_cutoff=0.5,
            )
            / 100.0
        )

        # 4. 詳細説明の類似度（トークンセット比較）
        if existing.description and new_data.description:
            # 両方ある場合: 4フィールド使用
            _existing_des = existing.description[: self.DESC_COMPARE_LENGTH]
            _new_des = new_data.description[: self.DESC_COMPARE_LENGTH]
            # 詳細説明の長さで場合分け
            if len(_existing_des) <= 20 and len(_new_des) <= 20:
                desc_score = (
                    fuzz.token_set_ratio(
                        _existing_des,
                        _new_des,
                        processor=lambda s: self.decompose_text(s, noun_only=False),
                        score_cutoff=0.8,
                    )
                    / 100.0
                )
            else:
                desc_score = (
                    fuzz.partial_token_set_ratio(
                        _existing_des,
                        _new_des,
                        processor=lambda s: self.decompose_text(s, noun_only=False),
                        score_cutoff=0.6,
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

    @lru_cache
    def decompose_text(self, text: str, noun_only: bool = False) -> str:
        """テキストの形態素解析をしトークンごとに分かち書きした文字列を返却

        - token_set_ratio, token_sort_ratio用
        """
        normalized = self.normalize_text(text)
        tokens = []
        for m in self.sudachi.tokenize(normalized, self.SPLIT_MODE):
            pos = m.part_of_speech()
            if noun_only and pos[0] != "名詞":
                continue
            tokens.append(m.surface())

        if not tokens:
            logger.warning("トークンが空です。原文を返却します。")
            return normalized
        return " ".join(tokens)

    @staticmethod
    def normalize_text(text: str) -> str:
        """全角半角・空白を揃えて比較の精度を上げる"""
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text).strip().replace(" ", "").replace("　", "")
