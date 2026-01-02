import asyncio
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from trail_status.models.llm_usage import LlmUsage
from trail_status.models.source import DataSource
from trail_status.services.llm_stats import TokenStats
from trail_status.services.pipeline import TrailConditionPipeline
from trail_status.services.schema import TrailConditionSchemaInternal
from trail_status.services.synchronizer import sync_trail_conditions
from trail_status.services.types import UpdatedDataList


class Command(BaseCommand):
    help = "登山道状況の自動スクレイピング・AI解析・DB同期パイプライン"

    def add_arguments(self, parser):
        parser.add_argument("--source", type=str, help="処理対象の情報源ID（指定しなければ全ての情報源を処理）")
        parser.add_argument(
            "--model",
            type=str,
            choices=["deepseek-reasoner", "deepseek-chat", "gemini-3-flash-preview", "gemini-2.5-flash"],
            default="deepseek-reasoner",
            help="使用するAIモデル (default: deepseek-reasoner)",
        )
        parser.add_argument("--dry-run", action="store_true", help="実際にDBに保存せず、処理結果のみ表示")

    def handle(self, *args, **options):
        source_id = options.get("source")
        model = options["model"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUNモード: DBには保存されません"))

        # 処理対象の情報源を取得（事前にデータを準備）
        if source_id:
            try:
                source = DataSource.objects.get(id=source_id)
                source_data_list = [{"id": source.id, "name": source.name, "url1": source.url1, "prompt_key": source.prompt_key}]
                self.stdout.write(f"情報源: {source.name}")
            except DataSource.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"指定された情報源が見つかりません: {source_id}"))
                return
        else:
            source_data_list = [{"id": s.id, "name": s.name, "url1": s.url1, "prompt_key": s.prompt_key} for s in DataSource.objects.all()]
            self.stdout.write(f"全ての情報源を処理: {len(source_data_list)}件")

        # パイプライン処理を実行（純粋にasync処理のみ）
        pipeline = TrailConditionPipeline()
        results = asyncio.run(pipeline.process_source_data(source_data_list, model))

        # DB保存（同期処理）
        if not dry_run:
            self.save_results_to_database(results)

        # 結果サマリーを表示
        summary = self.generate_summary(results)
        self.print_summary(summary)

    def save_results_to_database(self, results: UpdatedDataList):
        """処理結果をDBに保存"""

        for source_data, result in results:
            if result.get("success"):
                source = DataSource.objects.get(id=source_data["id"])
                # AIの結果をInternal schemaに変換
                new_trail_conditions = result["extracted_trail_conditions"]
                internal_data_list = [
                    TrailConditionSchemaInternal(**condition, url1=source_data["url1"]) for condition in new_trail_conditions
                ]

                # DB同期とLLM使用履歴記録
                with transaction.atomic():
                    sync_trail_conditions(source, internal_data_list)
                    self._save_llm_usage(source, result["stats"], len(new_trail_conditions))

                self.stdout.write(
                    self.style.SUCCESS(
                        f"DB保存完了: {source_data['name']} - {len(internal_data_list)}件 (コスト: ${result['stats']['total_fee']:.4f})"
                    )
                )

    def _save_llm_usage(self, source: DataSource, stats: TokenStats, conditions_count):
        """LLM使用履歴をDBに保存"""
        LlmUsage.objects.create(
            source=source,
            model=stats["model"],
            prompt_tokens=stats["input_tokens"],
            thinking_tokens=stats["thoughts_tokens"],
            output_tokens=stats["output_tokens"],
            cost_usd=Decimal(str(stats["total_fee"])),
            conditions_extracted=conditions_count,
            success=True,
            execution_time_seconds=stats.get("execution_time"),  # Noneでも可
        )

    def generate_summary(self, results: UpdatedDataList):
        """処理結果のサマリーを生成"""
        summary = {"results": [], "success_count": 0, "error_count": 0, "total_conditions": 0}

        for source_data, result in results:
            if result.get("success"):
                summary["results"].append(
                    {
                        "source_name": source_data["name"],
                        "status": "success",
                        "conditions_count": len(result.get("extracted_trail_conditions", [])),
                    }
                )
                summary["success_count"] += 1
                summary["total_conditions"] += len(result.get("extracted_trail_conditions", []))
            else:
                summary["results"].append(
                    {
                        "source_name": source_data["name"],
                        "status": "error",
                        "message": result.get("error", "Unknown error"),
                    }
                )
                summary["error_count"] += 1

        return summary

    def print_summary(self, summary: dict[str, Any]):
        """処理結果のサマリーを表示"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("処理結果サマリー")
        self.stdout.write("=" * 50)

        for result in summary["results"]:
            if result["status"] == "error":
                self.stdout.write(self.style.ERROR(f"❌ {result['source_name']}: {result['message']}"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {result['source_name']}: {result['conditions_count']}件の状況情報")
                )

        self.stdout.write(f"\n成功: {summary['success_count']}件, エラー: {summary['error_count']}件")
        self.stdout.write(f"取得された状況情報の総数: {summary['total_conditions']}件")
