"""
LLMクライアント（DeepSeek/Gemini）のテスト
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from trail_status.services.llm_client import DeepseekClient, GeminiClient, LlmConfig


class TestLlmClient:
    """LLMクライアントの基本機能テスト"""

    @pytest.fixture(autouse=True)
    def setup_config(self, mock_api_keys, sample_llm_config):
        """テスト用の設定準備"""
        self.config = LlmConfig(**sample_llm_config)

    def test_deepseek_client_initialization(self):
        """DeepSeekクライアントの初期化テスト"""
        client = DeepseekClient(self.config)
        assert client.model == "deepseek-chat"
        assert client.temperature == 0.3
        assert client.prompt == "テスト用プロンプト"

    def test_prompt_generation(self):
        """プロンプト生成テスト"""
        client = DeepseekClient(self.config)
        prompt = client.prompt_for_deepseek

        # JSON Schema指示が含まれているかチェック
        assert "Pydanticモデル" in prompt
        assert "テスト用プロンプト" in prompt
        assert "テスト用データ" in prompt

    @pytest.mark.asyncio
    async def test_deepseek_generate_success(self, monkeypatch, mock_openai_response):
        """DeepSeek API呼び出し成功テスト（モック使用）"""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        # AsyncOpenAI をモック
        mock_openai_class = MagicMock(return_value=mock_client)
        monkeypatch.setattr("trail_status.services.llm_client.AsyncOpenAI", mock_openai_class)

        client = DeepseekClient(self.config)

        # check_responseメソッドをモック化（Pydantic検証をスキップ）
        monkeypatch.setattr(client, "check_response", lambda x: {"conditions": []})

        data, stats = await client.generate()

        assert data == {"conditions": []}
        assert stats.token_stats.input_tokens == 100
        assert stats.token_stats.pure_output_tokens == 50
