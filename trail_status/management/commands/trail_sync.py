import asyncio
import logging
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from trail_status.models.condition import TrailCondition
from trail_status.models.llm_usage import LlmUsage
from trail_status.models.source import DataSource
from trail_status.services.llm_client import LlmConfig
from trail_status.services.llm_stats import LlmStats
from trail_status.services.pipeline import ModelDataSingle, ResultSingle, TrailConditionPipeline, UpdatedDataList
from trail_status.services.schema import (
    TrailConditionSchemaInternal,
    TrailConditionSchemaList,
)
from trail_status.services.synchronizer import sync_trail_conditions

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "登山道状況の自動スクレイピング・AI解析・DB同期パイプライン"

    def add_arguments(self, parser):
        parser.add_argument("--source", type=str, help="処理対象の情報源ID（指定しなければ全ての情報源を処理）")
        parser.add_argument(
            "--model",
            type=str,
            choices=["deepseek-reasoner", "deepseek-chat", "gemini-3-flash-preview", "gemini-2.5-flash"],
            help="使用するAIモデル（指定しなければプロンプトファイル設定またはデフォルトを使用）",
        )
        parser.add_argument("--dry-run", action="store_true", help="実際にDBに保存せず、処理結果のみ表示")

    def handle(self, *args, **options):
        source_id = options.get("source")
        ai_model = options.get("model")
        dry_run = options["dry_run"]

        logger.info(f"trail_sync コマンド開始 - source_id: {source_id}, model: {ai_model}, dry_run: {dry_run}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUNモード: DBには保存されません"))

        # 処理対象の情報源を取得（事前にデータを準備）
        if source_id:
            try:
                source = DataSource.objects.get(id=source_id)
                model_data_single = ModelDataSingle(
                    id=source.id,
                    name=source.name,
                    url1=source.url1,
                    prompt_key=source.prompt_key,
                    content_hash=source.content_hash,
                )
                source_data_list = [model_data_single]
                self.stdout.write(f"情報源: {source.name}")
            except DataSource.DoesNotExist:
                logger.error(f"指定された情報源が見つかりません: {source_id}")
                self.stdout.write(self.style.ERROR(f"指定された情報源が見つかりません: {source_id}"))
                return
        else:
            # CLI引数なしの場合すべての情報源を処理リストに追加
            source_data_list = [
                ModelDataSingle(id=s.id, name=s.name, url1=s.url1, prompt_key=s.prompt_key, content_hash=s.content_hash)
                for s in DataSource.objects.all()
            ]
            self.stdout.write(f"全ての情報源を処理: {len(source_data_list)}件")

        # パイプライン処理を実行（純粋にasync処理のみ）
        processor = TrailConditionPipeline()
        all_source_results: UpdatedDataList = asyncio.run(processor(source_data_list, ai_model))

        # DB保存（同期処理）
        if not dry_run:
            self.save_results_to_database(all_source_results)

        # 結果サマリーを表示
        summary = self.generate_summary(all_source_results)
        self.print_summary(summary)

    def save_results_to_database(self, results: UpdatedDataList) -> None:
        """処理結果をDBに保存"""
        from django.utils import timezone

        for source_data, result_by_source in results:
            if isinstance(result_by_source, ResultSingle) and result_by_source.success:
                source = DataSource.objects.get(id=source_data.id)
                # サイト巡回日時を更新
                # ハッシュ取得andLLMスキップ時も success=True
                source.last_checked_at = timezone.now()

                # コンテンツハッシュとスクレイピング時刻を更新
                if result_by_source.content_changed:
                    source.content_hash = result_by_source.new_hash
                    source.last_scraped_at = timezone.now()

                # コミット
                source.save(update_fields=["content_hash", "last_scraped_at", "last_checked_at"])

                # コンテンツ変更なしの場合はLLM関連処理をスキップ
                if not result_by_source.content_changed:
                    self.stdout.write(self.style.WARNING(f"コンテンツ変更なし: {source_data.name} - LLM処理スキップ"))
                    continue

                # AIの結果をInternal schemaに変換
                trail_conditions_list: TrailConditionSchemaList = result_by_source.extracted_trail_conditions

                # TrailCondition用のLLM設定(JSONField)
                ai_config = {
                    k: v
                    for k, v in {
                        "temperature": result_by_source.config.temperature,
                        "thinking_budget": result_by_source.config.thinking_budget,
                    }.items()
                    if v is not None
                }
                internal_data_list = [
                    TrailConditionSchemaInternal(**_by_sources.model_dump(), url1=source_data.url1, ai_config=ai_config)
                    for _by_sources in trail_conditions_list.trail_condition_records
                ]

                # DB同期とLLM使用履歴記録
                llm_stats: LlmStats = result_by_source.stats
                llm_config: LlmConfig = result_by_source.config
                prompt_filename = source.prompt_filename

                to_update, to_create = sync_trail_conditions(source, internal_data_list, llm_config, prompt_filename)
                with transaction.atomic():
                    self._save_trail_condition(to_update, to_create)
                    self._save_llm_usage(source, llm_stats, len(internal_data_list))

                logger.info(
                    f"DB保存完了: {source_data.name} - {len(internal_data_list)}件 (コスト: ${llm_stats.total_fee:.4f})"
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"DB保存完了: {source_data.name} - {len(internal_data_list)}件 (コスト: ${llm_stats.total_fee:.4f})"
                    )
                )

    def _save_trail_condition(self, to_update: list[TrailCondition], to_create: list[TrailCondition]) -> None:
        """TrailConditionをDBに保存"""
        from django.utils import timezone

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
            self.stdout.write(self.style.SUCCESS(f"更新完了: {len(to_update)}件"))
            logger.info(f"更新完了: {len(to_update)}件")

        if to_create:
            # bulk_createではauto_now_add=Trueが機能しないため手動でセット
            for record in to_create:
                record.created_at = now
                record.updated_at = now

            # 新規作成
            TrailCondition.objects.bulk_create(to_create)
            self.stdout.write(self.style.SUCCESS(f"新規作成完了: {len(to_create)}件"))
            logger.info(f"新規作成完了: {len(to_create)}件")

    def _save_llm_usage(self, source: DataSource, llm_stats: LlmStats, record_count: int) -> None:
        """LLM使用履歴をDBに保存"""
        stats = llm_stats.to_dict()
        LlmUsage.objects.create(
            source=source,
            model=stats["model"],
            prompt_tokens=stats["input_tokens"],
            thinking_tokens=stats["thoughts_tokens"],
            output_tokens=stats["output_tokens"],
            cost_usd=Decimal(str(stats["total_fee"])),
            conditions_extracted=record_count,
            success=True,
            execution_time_seconds=stats.get("execution_time"),  # Noneでも可
        )

    def generate_summary(self, results: UpdatedDataList) -> dict[str, Any]:
        """処理結果のサマリーを生成"""
        summary: dict[str, Any] = {
            "results": [],
            "success_count": 0,
            "error_count": 0,
            "skipped_count": 0,
            "total_conditions": 0,
        }

        for source_data, result in results:
            if isinstance(result, ResultSingle) and result.success:
                # コンテンツ変更なしの場合
                if not result.content_changed:
                    summary["results"].append(
                        {
                            "source_name": source_data.name,
                            "status": "skipped",
                            "reason": "コンテンツ変更なし",
                        }
                    )
                    summary["skipped_count"] += 1
                else:
                    # 正常処理の場合
                    conditions_count = self._get_conditions_count(result)
                    summary["results"].append(
                        {
                            "source_name": source_data.name,
                            "status": "success",
                            "conditions_count": conditions_count,
                        }
                    )
                    summary["success_count"] += 1
                    summary["total_conditions"] += conditions_count
            # スクレイピング失敗時
            elif isinstance(result, ResultSingle):
                summary["results"].append(
                    {
                        "source_name": source_data.name,
                        "status": "error",
                        "message": result.message,
                    }
                )
                summary["error_count"] += 1
            # BaseExceptionクラスだった場合
            else:
                summary["results"].append(
                    {
                        "source_name": source_data.name,
                        "status": "error",
                        "message": f"予期せぬエラー発生: {result}",
                    }
                )
                summary["error_count"] += 1

        return summary

    def _get_conditions_count(self, result: ResultSingle) -> int:
        """結果からレコード数を安全に取得"""
        if result.success:
            trail_conditions = result.extracted_trail_conditions
            if isinstance(trail_conditions, TrailConditionSchemaList):
                return len(trail_conditions.trail_condition_records)
        return 0

    def print_summary(self, summary: dict[str, Any]) -> None:
        """処理結果のサマリーを表示"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("処理結果サマリー")
        self.stdout.write("=" * 50)

        for result in summary["results"]:
            if result["status"] == "error":
                self.stdout.write(self.style.ERROR(f"❌ {result['source_name']}: {result['message']}"))
            elif result["status"] == "skipped":
                self.stdout.write(self.style.WARNING(f"⏭️  {result['source_name']}: {result['reason']}"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {result['source_name']}: {result['conditions_count']}件の状況情報")
                )

        self.stdout.write(
            f"\n成功: {summary['success_count']}件, スキップ: {summary['skipped_count']}件, エラー: {summary['error_count']}件"
        )
        self.stdout.write(f"取得された状況情報の総数: {summary['total_conditions']}件")
