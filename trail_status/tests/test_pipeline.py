from unittest.mock import AsyncMock, MagicMock

import pytest

from trail_status.services.llm_client import LlmConfig
from trail_status.services.pipeline import AiPipeline, SourceSchemaSingle
from trail_status.services.schema import TrailConditionSchemaList


@pytest.mark.asyncio
async def test_process_source_data_full_flow(monkeypatch, mock_async_client, sample_token_stats):
    # --- DeepseekClient.generate の戻り値を準備 ---
    mock_ai_result = TrailConditionSchemaList(trail_condition_records=[])

    # generateメソッドが呼ばれた際の戻り値を設定
    async_gen_mock = AsyncMock(return_value=(mock_ai_result, sample_token_stats))

    # クラスのメソッドを差し替え
    monkeypatch.setattr("trail_status.services.pipeline.DeepseekClient.generate", async_gen_mock)
    monkeypatch.setattr("trail_status.services.pipeline.GeminiClient.generate", async_gen_mock)
    monkeypatch.setattr("trail_status.services.pipeline.GptClient.generate", async_gen_mock)

    # --- LlmConfig.from_file のモック化 ---
    mock_config = LlmConfig(data="テスト", model="deepseek-chat")
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
    pipeline = AiPipeline(source_data_list, ai_model="deepseek-chat")

    results = await pipeline.run()

    # --- 検証 ---
    assert len(results) == 1
    source_data, result = results[0]

    assert result.success is True
    assert result.content_changed is True
