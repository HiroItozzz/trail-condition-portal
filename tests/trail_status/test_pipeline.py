from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from trail_status.services.llm_client import ConversationalAi, LlmConfig
from trail_status.services.llm_stats import TokenStats
from trail_status.services.pipeline import AiPipeline
from trail_status.services.types import ConditionSchemaAiList, SourceSchemaSingle

# --- テスト用 LLM クライアント ---


class FakeGeminiClient(ConversationalAi):
    """テスト用 GeminiClient モック"""

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
            input_letter_count=len(self.prompt),
            output_letter_count=len(raw_response.text),
            model=self.model,
        )

    async def _handle_exceptions(self, e, retry_count, max_retries):
        raise e


@pytest.mark.asyncio
async def test_process_source_data_full_flow(monkeypatch, mock_async_client):
    """パイプラインの全体フロー検証（Gemini クライアント使用）

    - httpx.AsyncClient: mock_async_client でモック化
    - LLMクライアント: FakeGeminiClient で ConversationalAi メソッドをモック化
    - リトライ・エラーハンドリングは実装動作を検証
    """
    # --- LlmConfig.from_file のモック化 ---
    mock_config = LlmConfig(data="テスト", model="gemini-2.5-flash", site_prompt="テストプロンプト")
    monkeypatch.setattr("trail_status.services.pipeline.LlmConfig.from_file", MagicMock(return_value=mock_config))

    # --- テスト用ソースデータ ---
    source_data_list = [
        SourceSchemaSingle(
            id=1,
            name="テスト山",
            url1="https://example.com/test",
            prompt_key="standard",
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
