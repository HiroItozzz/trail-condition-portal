from pathlib import Path

from trail_status.models import DataSource


def _handle_all_sources(self, file_gen: int, ai_model: str, force_sync: bool):
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
            source = DataSource.web.get(id=source_id)
        except DataSource.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"スキップ: DataSource ID {source_id} が見つかりません"))
            continue

        # 最新JSONファイルを取得
        json_files = sorted(sample_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if ai_model:
            json_files = [f for f in json_files if f.stem.startswith(ai_model)]

        if not json_files:
            self.stdout.write(self.style.WARNING(f"スキップ: JSONファイルが見つかりません: {dir_name}"))
            continue

        latest_file = json_files[min(len(json_files) - 1, file_gen)]

        # 照合テストを実行
        try:
            result = self._test_matching_for_source(source, str(latest_file), force_sync=force_sync)
            if result:
                all_results.append(
                    {
                        "source": source,
                        "file": latest_file.name,
                        "update_count": result["update_count"],
                        "create_count": result["create_count"],
                        "total_count": result["total_count"],
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
