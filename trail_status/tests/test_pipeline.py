from unittest.mock import AsyncMock, MagicMock

import pytest
from trail_status.services.pipeline import TrailConditionPipeline



@pytest.mark.asyncio
async def test_process_source_data_full_flow(monkeypatch, mock_async_client, sample_token_stats):
    # --- DeepseekClient.generate の戻り値を準備 ---
    mock_ai_result = MagicMock() 
    

    # generateメソッドが呼ばれた際の戻り値を設定
    async_gen_mock = AsyncMock(return_value=(mock_ai_result, sample_token_stats))

    # クラスのメソッドを差し替え
    monkeypatch.setattr("trail_status.services.pipeline.DeepseekClient.generate", async_gen_mock)
    monkeypatch.setattr("trail_status.services.pipeline.GeminiClient.generate", async_gen_mock)

    # --- LlmConfig.from_file のモック化 ---
    mock_config = MagicMock()
    mock_config.model = "deepseek-chat"
    monkeypatch.setattr("trail_status.services.pipeline.LlmConfig.from_file", MagicMock(return_value=mock_config))

    # --- テスト実行 ---
    pipeline = TrailConditionPipeline()
    source_data_list = [
        {
            "id": 1,
            "name": "テスト山",
            "url1": "https://example.com/test",
            "prompt_key": "standard",
            "content_hash": None,
        }
    ]

    results = await pipeline.process_source_data(source_data_list, "deepseek-chat")

    # --- 検証 ---
    assert len(results) == 1
    source_data, result = results[0]

    # これで KeyError: 'success' が消えるはずです
    assert result["success"] is True
    assert result["content_changed"] is True