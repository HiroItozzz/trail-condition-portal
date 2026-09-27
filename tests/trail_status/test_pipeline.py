from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from tenacity import wait_none

from trail_status.services.fetcher import DataFetcher
from trail_status.services.llm_client import ConversationalAi, LlmConfig
from trail_status.services.llm_stats import TokenStats
from trail_status.services.pipeline import AiPipeline
from trail_status.services.prompt_utils import PromptFile
from trail_status.services.types import ConditionSchemaAiList, SourceSchemaSingle

# --- テスト用 LLM クライアント ---


class FakeGeminiClient(ConversationalAi):
    """テスト用 GeminiClient モック"""

    @property
    def prompt_with_data(self):
        return ""

    async def _call_api(self):
        """Gemini response の構造を模倣"""
        return SimpleNamespace(
            text='{"trail_condition_records": []}',
            usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=50, thoughts_token_count=10),
        )

    def _extract_text(self, raw_response):
        return raw_response.text

    def _get_validated_data(self, raw_response):
        return ConditionSchemaAiList.model_validate_json(self._extract_text(raw_response))

    def _create_token_stats(self, raw_response):
        usage = raw_response.usage_metadata
        return TokenStats(
            input_tokens=usage.prompt_token_count,
            thoughts_tokens=usage.thoughts_token_count or 0,
            pure_output_tokens=usage.candidates_token_count,
            input_letter_count=len(self.config.prompt),
            output_letter_count=len(raw_response.text),
            model=self.config.model,
        )

    async def _handle_exceptions(self, e, retry_count, max_retries):
        raise e


class FailingGeminiClient(FakeGeminiClient):
    """LLM呼び出しが必ず失敗するテスト用クライアント"""

    async def _call_api(self):
        raise RuntimeError("LLM失敗")


class TestPipeline:
    def setup_method(self):

        self.template_config = {
            "prompt": "テストプロンプト",
            "config": {"model": "gemini-test-template", "temperature": 1.8, "thinking_budget": 20000},
        }
        self.individual_config = {
            "prompt": "個別プロンプト",
            "config": {"model": "gpt-test-individual", "temperature": 0.2, "thinking_budget": 50, "use_template": True},
        }

    @pytest.mark.asyncio
    async def test_process_source_data_full_flow(self, monkeypatch, mock_api_keys, mock_async_client):
        """パイプラインの全体フロー検証（Gemini クライアント使用）

        - httpx.AsyncClient: mock_async_client でモック化
        - LLMクライアント: FakeGeminiClient で ConversationalAi メソッドをモック化
        - リトライ・エラーハンドリングは実装動作を検証
        """
        # --- LlmConfig.from_file のモック化 ---
        mock_config = LlmConfig(data="テスト", model="gemini-2.5-flash", prompt="テストプロンプト")
        monkeypatch.setattr("trail_status.services.pipeline.LlmConfig.from_file", MagicMock(return_value=mock_config))

        # --- テスト用ソースデータ ---
        source_data_list = [
            SourceSchemaSingle(
                id=1,
                name="テスト山",
                url1="https://example.com/test",
                prompt_file=PromptFile(prompt="test"),
                content_hash=None,
            )
        ]

        # --- テスト実行 ---
        # client_factory で FakeGeminiClient を生成
        pipeline = AiPipeline(source_data_list, client_factory=lambda config: FakeGeminiClient(config))
        results = await pipeline.run()

        # --- 検証 ---
        assert len(results) == 1
        source_data, result = results[0]

        assert result.success is True
        assert result.content_changed is True
        assert result.stats is not None
        assert result.extracted_trail_conditions is not None

    @pytest.mark.asyncio
    async def test_hash_match_skips_llm(self, monkeypatch, mock_api_keys, mock_async_client):
        """ハッシュが一致する場合はLLM処理をスキップする"""
        html = "<html><body><p>登山道状況に変更はありません。</p></body></html>"
        mock_async_client.get.return_value.text = html

        url = "https://example.com/test"
        content_hash = DataFetcher(url).calculate_content_hash(html)

        mock_config = LlmConfig(data="テスト", model="gemini-2.5-flash", prompt="テストプロンプト")
        monkeypatch.setattr("trail_status.services.pipeline.LlmConfig.from_file", MagicMock(return_value=mock_config))

        source_data_list = [
            SourceSchemaSingle(
                id=1,
                name="テスト山",
                url1=url,
                prompt_file=PromptFile(prompt="test"),
                content_hash=content_hash,
            )
        ]

        client_factory = MagicMock(side_effect=lambda config: FakeGeminiClient(config))
        pipeline = AiPipeline(source_data_list, client_factory=client_factory)
        results = await pipeline.run()

        assert len(results) == 1
        source_data, result = results[0]

        assert result.success is True
        assert result.content_changed is False
        assert result.new_hash == content_hash
        assert result.extracted_trail_conditions is None
        client_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_hash_match_with_new_hash_mode_calls_llm(self, monkeypatch, mock_api_keys, mock_async_client):
        """ハッシュが一致してもnew_hash_mode=Trueなら既存データを上書きするためLLMを呼ぶ"""
        html = "<html><body><p>登山道状況に変更はありません。</p></body></html>"
        mock_async_client.get.return_value.text = html

        url = "https://example.com/test"
        content_hash = DataFetcher(url).calculate_content_hash(html)

        mock_config = LlmConfig(data="テスト", model="gemini-2.5-flash", prompt="テストプロンプト")
        monkeypatch.setattr("trail_status.services.pipeline.LlmConfig.from_file", MagicMock(return_value=mock_config))

        source_data_list = [
            SourceSchemaSingle(
                id=1,
                name="テスト山",
                url1=url,
                prompt_file=PromptFile(prompt="test"),
                content_hash=content_hash,
            )
        ]

        client_factory = MagicMock(side_effect=lambda config: FakeGeminiClient(config))
        pipeline = AiPipeline(source_data_list, client_factory=client_factory, new_hash_mode=True)
        results = await pipeline.run()

        assert len(results) == 1
        source_data, result = results[0]

        assert result.success is True
        assert result.content_changed is True
        client_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_scraped_result_fails(self, mock_api_keys, mock_async_client):
        """スクレイピング結果が空文字（実質空白のみ）の場合は失敗として扱う"""
        mock_async_client.get.return_value.text = "   "

        source_data_list = [
            SourceSchemaSingle(
                id=1,
                name="テスト山",
                url1="https://example.com/test",
                prompt_file=PromptFile(prompt="test"),
                content_hash=None,
            )
        ]

        client_factory = MagicMock(side_effect=lambda config: FakeGeminiClient(config))
        pipeline = AiPipeline(source_data_list, client_factory=client_factory)
        results = await pipeline.run()

        assert len(results) == 1
        source_data, result = results[0]

        assert result.success is False
        assert result.message == "スクレイピング結果が空でした"
        client_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_http_failure_is_reported_after_retries(self, monkeypatch, mock_api_keys, mock_async_client):
        """HTTP取得が毎回失敗する場合は3回リトライした上で処理エラーになる"""
        mock_async_client.get.side_effect = httpx.ConnectError("接続失敗")
        # リトライの待ち時間を0にしてテストを高速化
        monkeypatch.setattr(DataFetcher.fetch_html.retry, "wait", wait_none())

        source_data_list = [
            SourceSchemaSingle(
                id=1,
                name="テスト山",
                url1="https://example.com/test",
                prompt_file=PromptFile(prompt="test"),
                content_hash=None,
            )
        ]

        client_factory = MagicMock(side_effect=lambda config: FakeGeminiClient(config))
        pipeline = AiPipeline(source_data_list, client_factory=client_factory)
        results = await pipeline.run()

        assert len(results) == 1
        source_data, result = results[0]

        assert result.success is False
        assert result.message.startswith("処理エラー")
        assert mock_async_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_llm_failure_is_reported(self, monkeypatch, mock_api_keys, mock_async_client):
        """LLM呼び出しが例外を投げた場合は処理エラーとしてメッセージに含める"""
        mock_config = LlmConfig(data="テスト", model="gemini-2.5-flash", prompt="テストプロンプト")
        monkeypatch.setattr("trail_status.services.pipeline.LlmConfig.from_file", MagicMock(return_value=mock_config))

        source_data_list = [
            SourceSchemaSingle(
                id=1,
                name="テスト山",
                url1="https://example.com/test",
                prompt_file=PromptFile(prompt="test"),
                content_hash=None,
            )
        ]

        pipeline = AiPipeline(source_data_list, client_factory=lambda config: FailingGeminiClient(config))
        results = await pipeline.run()

        assert len(results) == 1
        source_data, result = results[0]

        assert result.success is False
        assert "LLM失敗" in result.message

    @pytest.mark.asyncio
    async def test_one_of_multiple_sources_fails(self, monkeypatch, mock_api_keys, mock_async_client):
        """複数の情報源のうち1件だけLLM処理に失敗しても、他の結果は入力と同じ順で返る"""
        mock_config = LlmConfig(data="テスト", model="gemini-2.5-flash", prompt="テストプロンプト")
        monkeypatch.setattr("trail_status.services.pipeline.LlmConfig.from_file", MagicMock(return_value=mock_config))

        # config内容ではクライアントを区別できないため、呼ばれた回数で1件目だけ失敗させる
        call_count = 0

        def client_factory(config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FailingGeminiClient(config)
            return FakeGeminiClient(config)

        source_data_list = [
            SourceSchemaSingle(
                id=1,
                name="テスト山1",
                url1="https://example.com/test1",
                prompt_file=PromptFile(prompt="test1"),
                content_hash=None,
            ),
            SourceSchemaSingle(
                id=2,
                name="テスト山2",
                url1="https://example.com/test2",
                prompt_file=PromptFile(prompt="test2"),
                content_hash=None,
            ),
        ]

        pipeline = AiPipeline(source_data_list, client_factory=client_factory)
        results = await pipeline.run()

        assert len(results) == 2
        assert results[0][0].id == 1
        assert results[0][1].success is False
        assert results[1][0].id == 2
        assert results[1][1].success is True
