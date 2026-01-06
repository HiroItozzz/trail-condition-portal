import asyncio
from pprint import pprint

from django.conf import settings
from django.core.management.base import BaseCommand

from trail_status.services.llm_client import DeepseekClient, GeminiClient, LlmConfig


class Command(BaseCommand):
    help = "LLMクライアントのテスト実行"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            choices=["deepseek", "gemini", "both"],
            default="deepseek",
            help="テストするモデル (default: deepseek)",
        )
        parser.add_argument(
            "--config", type=str, default="okutama_vc", help="使用する設定ファイル名 (default: okutama_vc)"
        )

    def handle(self, *args, **options):
        model_choice = options["model"]
        config_name = options["config"]

        self.stdout.write(f"LLMテストを開始: {model_choice}, 設定: {config_name}")

        try:
            # サンプルデータを読み込み
            data = self.load_test_data(config_name)

            if model_choice == "deepseek":
                results = self.test_deepseek(config_name, data)
            elif model_choice == "gemini":
                results = self.test_gemini(config_name, data)
            elif model_choice == "both":
                results = self.test_both_models(config_name, data)

            self.print_results(results)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"テスト実行中にエラーが発生: {e}"))
            raise

    def load_test_data(self, config_name):
        """テスト用データを読み込み"""
        # Django設定からベースディレクトリを取得
        base_dir = settings.BASE_DIR
        data_path = base_dir / "trail_status" / "services" / "sample" / f"sample_{config_name}.txt"

        if not data_path.exists():
            raise FileNotFoundError(f"サンプルファイルが見つかりません: {data_path}")

        data = data_path.read_text(encoding="utf-8")
        return data

    def test_deepseek(self, config_name, data):
        """DeepSeekのみテスト"""
        self.stdout.write("DeepSeekテストを実行中...")
        d_config = LlmConfig.from_site(config_name, data=data, model="deepseek-reasoner")
        return [asyncio.run(DeepseekClient(d_config).generate())]

    def test_gemini(self, config_name, data):
        """Geminiのみテスト"""
        self.stdout.write("Geminiテストを実行中...")
        g_config = LlmConfig.from_site(config_name, data=data, model="gemini-3-flash-preview")
        return [asyncio.run(GeminiClient(g_config).generate())]

    def test_both_models(self, config_name, data):
        """両方のモデルを並行テスト"""
        self.stdout.write("両方のモデルを並行テスト中...")

        async def run_both():
            d_config = LlmConfig.from_site(config_name, data=data, model="deepseek-reasoner")
            g_config = LlmConfig.from_site(config_name, data=data, model="gemini-3-flash-preview")

            return await asyncio.gather(
                DeepseekClient(d_config).generate(), GeminiClient(g_config).generate(), return_exceptions=True
            )

        return asyncio.run(run_both())

    def print_results(self, results):
        """結果を整形して出力"""
        for idx, result in enumerate(results, 1):
            if isinstance(result, Exception):
                self.stdout.write(self.style.ERROR(f"結果{idx}: エラーが発生 - {result}"))
                continue

            output, stats = result

            self.stdout.write(f"\n==================結果{idx}=======================")
            self.stdout.write("\n=======AIによる出力=======")
            pprint(output)
            self.stdout.write("=======AIによるコスト分析=======")
            pprint(stats.__dict__)
            self.stdout.write("")
