from unittest.mock import MagicMock

import pytest

from trail_status.services.llm_client import ConversationalAi, LlmConfig
from trail_status.services.pipeline import AiPipeline, SourceSchemaSingle
from trail_status.services.schema import TrailConditionSchemaList


@pytest.mark.asyncio
async def test_process_source_data_full_flow(monkeypatch, mock_async_client, sample_token_stats):
    class FakeClient(ConversationalAi):
        async def generate(self):
            return fake_ai_result, sample_token_stats

    # --- ConversationalAi.generate の戻り値を準備 ---
    fake_ai_result = TrailConditionSchemaList(trail_condition_records=[])

    # --- LlmConfig.from_file のモック化 ---
    mock_config = LlmConfig(data="テスト", model="gemini-2.5-flash")
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
    pipeline = AiPipeline(source_data_list, client_factory=lambda config: FakeClient(config))

    results = await pipeline.run()

    # --- 検証 ---
    assert len(results) == 1
    source_data, result = results[0]

    assert result.success is True
    assert result.content_changed is True
