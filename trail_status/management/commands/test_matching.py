import json
from pathlib import Path

from django.core.management.base import BaseCommand

from trail_status.models.source import DataSource
from trail_status.services.db_writer import DbWriter
from trail_status.services.llm_client import LlmConfig
from trail_status.services.pipeline import ResultSingle, SourceSchemaSingle
from trail_status.services.schema import TrailConditionSchemaInternal


class Command(BaseCommand):
    help = "サンプルJSONからRapidFuzz照合ロジックをテスト（DB保存なし、照合結果のみ表示）"

    def add_arguments(self, parser):
        parser.add_argument("--source", type=int, help="DataSourceのID（指定しない場合は全ての情報源を処理）")
        parser.add_argument(
            "--json-file", type=str, help="AI出力JSONファイルのパス（指定しない場合は最新サンプルJSONを使用）"
        )
        parser.add_argument("--json-data", type=str, help="AI出力JSON文字列（直接入力）")

    def handle(self, *args, **options):
        source_id = options.get("source")
        json_file = options.get("json_file")
        json_data = options.get("json_data")

        # 全情報源を処理する場合
        if source_id is None:
            self._handle_all_sources()
        else:
            # 単一情報源を処理
            self._handle_single_source(source_id, json_file, json_data)

    def _handle_all_sources(self):
        """全ての情報源について照合テストを実行"""
        sample_base_dir = Path("trail_status/services/sample")

        if not sample_base_dir.exists():
            self.stdout.write(self.style.ERROR(f"サンプルディレクトリが見つかりません: {sample_base_dir}"))
            return

        # サンプルディレクトリをスキャン
        sample_dirs = [d for d in sample_base_dir.iterdir() if d.is_dir()]
        if not sample_dirs:
            self.stdout.write(self.style.ERROR("サンプルディレクトリが見つかりません"))
            return

        self.stdout.write(f"サンプルディレクトリ: {len(sample_dirs)}件見つかりました\n")

        # 全体の結果を集計
        all_results = []
        total_update = 0
        total_create = 0
        total_records = 0

        for sample_dir in sorted(sample_dirs):
            # ディレクトリ名から情報源を特定（例: 001_okutama_vc → ID=1）
            dir_name = sample_dir.name
            try:
                source_id = int(dir_name.split("_")[0])
            except (ValueError, IndexError):
                self.stdout.write(self.style.WARNING(f"スキップ: ディレクトリ名が不正です: {dir_name}"))
                continue

            # DataSourceを取得
            try:
                source = DataSource.objects.get(id=source_id)
            except DataSource.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"スキップ: DataSource ID {source_id} が見つかりません"))
                continue

            # 最新JSONファイルを取得
            json_files = sorted(sample_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not json_files:
                self.stdout.write(self.style.WARNING(f"スキップ: JSONファイルが見つかりません: {dir_name}"))
                continue

            latest_file = json_files[0]

            # 照合テストを実行
            try:
                result = self._test_matching_for_source(source, str(latest_file))
                if result:
                    duplicate_count = len(result.get("duplicate_warnings", []))
                    all_results.append(
                        {
                            "source": source,
                            "file": latest_file.name,
                            "update_count": result["update_count"],
                            "create_count": result["create_count"],
                            "total_count": result["total_count"],
                            "duplicate_count": duplicate_count,
                        }
                    )
                    total_update += result["update_count"]
                    total_create += result["create_count"]
                    total_records += result["total_count"]
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"エラー: {source.name} - {str(e)}"))
                continue

        # 全体のサマリーを表示
        self._print_all_sources_summary(all_results, total_update, total_create, total_records)

    def _handle_single_source(self, source_id, json_file, json_data):
        """単一情報源について照合テストを実行"""
        # DataSourceを取得
        try:
            source = DataSource.objects.get(id=source_id)
            self.stdout.write(f"データソース: {source.name}\n")
        except DataSource.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"DataSource ID {source_id} が見つかりません"))
            return

        # JSONの取得方法を決定
        if not json_file and not json_data:
            # 最新サンプルJSONを使うか確認
            sample_dir = Path("trail_status/services/sample") / f"{source.id:03d}_{source.prompt_key}"

            if not sample_dir.exists():
                self.stdout.write(self.style.ERROR(f"サンプルディレクトリが見つかりません: {sample_dir}"))
                self.stdout.write("--json-file または --json-data を指定してください")
                return

            json_files = sorted(sample_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not json_files:
                self.stdout.write(self.style.ERROR(f"サンプルJSONファイルが見つかりません: {sample_dir}"))
                return

            latest_file = json_files[0]
            self.stdout.write(f"使用サンプルファイル: {latest_file.name}")

            json_file = str(latest_file)
            self.stdout.write(self.style.SUCCESS(f"使用ファイル: {json_file}\n"))

        # 照合テストを実行
        try:
            result = self._test_matching_for_source(source, json_file, json_data)
            if result:
                # 単一情報源用の詳細表示
                self._print_matching_results(
                    result["to_update"],
                    result["to_create"],
                    result["total_count"],
                    result.get("duplicate_warnings", [])
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"エラーが発生: {e}"))
            self.stdout.write(self.style.WARNING("処理を中断しました"))

    def _test_matching_for_source(self, source, json_file=None, json_data=None):
        """指定された情報源とJSONファイルで照合テストを実行"""
        # JSONデータを読み込み & モデル名を抽出
        if json_file:
            with open(json_file, "r", encoding="utf-8") as f:
                ai_output = json.load(f)
            # ファイル名からモデル名を抽出
            json_path = Path(json_file)
            model_name = json_path.stem.split("_")[0]
        elif json_data:
            ai_output = json.loads(json_data)
            model_name = "test-from-json-data"
        else:
            return None

        # ai_outputが既にtrail_condition_records形式か確認
        if "trail_condition_records" in ai_output:
            ai_conditions = ai_output["trail_condition_records"]
        elif "conditions" in ai_output:
            ai_conditions = ai_output["conditions"]
        else:
            self.stdout.write(self.style.ERROR('JSONに"trail_condition_records"または"conditions"キーが見つかりません'))
            return None

        # AI config（ダミー）
        ai_config = {"temperature": 0}

        # TrailConditionSchemaInternalリストを作成
        internal_data_list = [
            TrailConditionSchemaInternal(**record, url1=source.url1, ai_config=ai_config) for record in ai_conditions
        ]

        # SourceSchemaSingleを作成
        source_schema = SourceSchemaSingle(
            id=source.id,
            name=source.name,
            url1=source.url1,
            prompt_key=source.prompt_key,
            content_hash=source.content_hash,
        )

        # LlmConfigをダミーで作成（照合ロジックで使用）
        config = LlmConfig(model=model_name, data="", temperature=0)

        # ResultSingle（最小限のダミー）
        result = ResultSingle(
            success=True,
            content_changed=True,
            config=config,
            message="Test matching only",
        )

        # 重複警告コールバック（リアルタイム表示用）
        def on_duplicate(dup_info):
            self.stdout.write(
                self.style.ERROR(
                    f"⚠️  重複照合警告: レコードID {dup_info['record_id']}\n"
                    f"    既存: {dup_info['existing_mountain']}/{dup_info['existing_trail']}\n"
                    f"    新規: {dup_info['new_mountain']}/{dup_info['new_trail']}\n"
                    f"    → スキップします"
                )
            )

        # DbWriterで照合ロジックを実行（DB保存なし）
        writer = DbWriter(source_schema, result, on_duplicate_warning=on_duplicate)
        to_update, to_create, duplicate_warnings = writer._reconcile_records(internal_data_list)

        return {
            "to_update": to_update,
            "to_create": to_create,
            "update_count": len(to_update),
            "create_count": len(to_create),
            "total_count": len(internal_data_list),
            "duplicate_warnings": duplicate_warnings,
        }

    def _print_matching_results(self, to_update, to_create, total_count, duplicate_warnings):
        """照合結果を整形して表示（単一情報源用）"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("照合結果サマリー"))
        self.stdout.write("=" * 60 + "\n")

        update_count = len(to_update)
        create_count = len(to_create)
        duplicate_count = len(duplicate_warnings)

        self.stdout.write(f"総レコード数: {total_count}件")
        self.stdout.write(f"既存レコード更新: {update_count}件")
        self.stdout.write(f"新規レコード作成: {create_count}件")
        if duplicate_count > 0:
            self.stdout.write(self.style.WARNING(f"重複スキップ: {duplicate_count}件"))
        self.stdout.write("")

        # 重複警告の詳細表示
        if duplicate_warnings:
            self.stdout.write(self.style.WARNING("【重複照合警告】"))
            for dup in duplicate_warnings:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  レコードID {dup['record_id']}: "
                        f"{dup['existing_mountain']}/{dup['existing_trail']} と "
                        f"{dup['new_mountain']}/{dup['new_trail']} が重複"
                    )
                )
            self.stdout.write(self.style.WARNING("  → プロンプトの見直しを推奨します\n"))

        # 更新対象の詳細
        if to_update:
            self.stdout.write(self.style.WARNING("【更新対象レコード】"))
            for record in to_update:
                self.stdout.write(
                    f"  ID: {record.id} | {record.mountain_name_raw} / {record.trail_name} | {record.status}"
                )
            self.stdout.write("")

        # 新規作成の詳細
        if to_create:
            self.stdout.write(self.style.SUCCESS("【新規作成レコード】"))
            for record in to_create:
                self.stdout.write(f"  {record.mountain_name_raw} / {record.trail_name} | {record.status}")
            self.stdout.write("")

        self.stdout.write("=" * 60)
        self.stdout.write(
            self.style.SUCCESS(f"✅ 照合完了: 更新 {update_count}件 / 新規 {create_count}件 / 合計 {total_count}件")
        )
        self.stdout.write("=" * 60)

    def _print_all_sources_summary(self, all_results, total_update, total_create, total_records):
        """全情報源の照合結果サマリーを表示"""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("全情報源 照合結果サマリー"))
        self.stdout.write("=" * 70 + "\n")

        total_duplicates = 0
        for result in all_results:
            source = result["source"]
            duplicate_count = result.get("duplicate_count", 0)
            total_duplicates += duplicate_count

            status = (
                f"更新: {result['update_count']}件 / 新規: {result['create_count']}件 / 合計: {result['total_count']}件"
            )
            if duplicate_count > 0:
                status += self.style.WARNING(f" / 重複: {duplicate_count}件")

            self.stdout.write(f"✅ {source.name} ({result['file']})\n   {status}\n")

        self.stdout.write("=" * 70)
        summary_text = f"総合計: 更新 {total_update}件 / 新規 {total_create}件 / 全レコード {total_records}件"
        if total_duplicates > 0:
            summary_text += f" / 重複スキップ {total_duplicates}件"
        self.stdout.write(self.style.SUCCESS(summary_text))
        self.stdout.write(f"処理した情報源: {len(all_results)}件")
        if total_duplicates > 0:
            self.stdout.write(self.style.WARNING("⚠️  重複照合が発生しています。プロンプトの見直しを推奨します。"))
        self.stdout.write("=" * 70)
