"""
LLMクライアント（DeepSeek/Gemini）のテスト
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from trail_status.services.llm_client import DeepseekClient, GeminiClient, LlmConfig


@pytest.fixture
def config(mock_api_keys, sample_llm_config):
    """テスト用のLlmConfig"""
    return LlmConfig(**sample_llm_config)


def test_deepseek_client_initialization(config):
    """DeepSeekクライアントの初期化テスト"""
    client = DeepseekClient(config)
    assert client.model == "deepseek-chat"
    assert client.temperature == 0.3
    assert client.prompt == "テスト用プロンプト"


def test_prompt_generation(config):
    """プロンプト生成テスト"""
    client = DeepseekClient(config)
    prompt = client.prompt_for_deepseek

    # JSON Schema指示が含まれているかチェック
    assert "Pydanticモデル" in prompt
    assert "テスト用プロンプト" in prompt
    assert "テスト用データ" in prompt


@pytest.mark.asyncio
async def test_deepseek_generate_success(config, monkeypatch, mock_openai_response):
    """DeepSeek API呼び出し成功テスト（モック使用）"""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

    # openai.AsyncOpenAI をモック（メソッド内でインポートされるため）
    mock_openai_class = MagicMock(return_value=mock_client)
    monkeypatch.setattr("openai.AsyncOpenAI", mock_openai_class)

    client = DeepseekClient(config)

    # validate_responseメソッドをモック化（Pydantic検証をスキップ）
    from trail_status.services.schema import TrailConditionSchemaList
    mock_validated_data = TrailConditionSchemaList(trail_condition_records=[])
    monkeypatch.setattr(client, "validate_response", lambda x: mock_validated_data)

    validated_data, token_stats = await client.generate()

    assert isinstance(validated_data, TrailConditionSchemaList)
    assert len(validated_data.trail_condition_records) == 0
    assert token_stats.input_tokens == 100
    assert token_stats.pure_output_tokens == 50
