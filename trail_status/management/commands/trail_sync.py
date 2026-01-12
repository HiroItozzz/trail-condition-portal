import asyncio
import logging
from typing import Any

from django.core.management.base import BaseCommand

from trail_status.models.source import DataSource
from trail_status.services.db_writer import DbWriter
from trail_status.services.pipeline import ResultSingle, SourceSchemaSingle, TrailConditionPipeline, UpdatedDataList
from trail_status.services.schema import TrailConditionSchemaList

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "登山道状況の自動スクレイピング・AI解析・DB同期パイプライン"

    def add_arguments(self, parser):
        parser.add_argument("--source", type=str, help="処理対象の情報源ID（指定しなければ全ての情報源を処理）")
        parser.add_argument(
            "--model",
            type=str,
            choices=[
                "deepseek-reasoner",
                "deepseek-chat",
                "gemini-3-flash-preview",
                "gemini-2.5-flash",
                "gpt-5-mini",
                "gpt-5-nano",
            ],
            help="使用するAIモデル（指定しなければプロンプトファイル設定またはデフォルトを使用）",
        )
        parser.add_argument("--dry-run", action="store_true", help="実際にDBに保存せず、処理結果のみ表示")
        parser.add_argument("--new-hash", action="store_true", help="既存のハッシュを無視しLlm処理実行")

    def handle(self, *args, **options):
        source_id = options.get("source")
        ai_model = options.get("model")
        dry_run = options["dry_run"]
        new_hash = options["new_hash"]

        logger.info(
            f"trail_sync コマンド開始 - source_id: {source_id}, model: {ai_model}, dry_run: {dry_run}, new_hash: {new_hash}"
        )

        if new_hash:
            self.stdout.write(self.style.WARNING("NEW-HASHモード: 更新のないサイトデータも変更されます。本当に実行しますか？"))
            choice = input("(y/N): ")
            if choice != "y":
                self.stdout.write(self.style.WARNING("実行を中断します。"))
                return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUNモード: DBには保存されません"))
        
        # 処理対象の情報源を取得（事前にデータを準備）
        if source_id:
            try:
                source = DataSource.objects.get(id=source_id)
                model_data_single = SourceSchemaSingle(
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
                SourceSchemaSingle(
                    id=s.id, name=s.name, url1=s.url1, prompt_key=s.prompt_key, content_hash=s.content_hash
                )
                for s in DataSource.objects.all()
            ]
            self.stdout.write(f"全ての情報源を処理: {len(source_data_list)}件")

        # パイプライン処理を実行（純粋にasync処理のみ）
        processor = TrailConditionPipeline(source_data_list, ai_model=ai_model, new_hash=new_hash)
        all_source_results: UpdatedDataList = asyncio.run(processor.run())

        # DB保存（同期処理）
        if not dry_run:
            for source_data, result_by_source in all_source_results:
                if isinstance(result_by_source, ResultSingle) and result_by_source.success:
                    writer = DbWriter(source_data, result_by_source)
                    writer.save_to_source()

                    if not result_by_source.content_changed:
                        if not new_hash:
                            self.stdout.write(
                                self.style.WARNING(f"コンテンツ変更なし: {source_data.name} - LLM処理スキップ")
                            )
                            continue
                        else:
                            logger.info("NEW-HASHモード: 既存データと再度照合します")

                    db_result = writer.save_condition_and_usage()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"DB保存完了: {db_result['name']}\n更新: {db_result['updated']}件 - 新規作成: {db_result['created']}件 - 計: {db_result['count']}件 (コスト: ${db_result['cost']:.4f})"
                        )
                    )

        # 結果サマリーを表示
        summary = self.generate_summary(all_source_results)
        self.print_summary(summary)

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
