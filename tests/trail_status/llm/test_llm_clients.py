"""
LLMクライアント（DeepSeek/Gemini）のテスト
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, ValidationError

from trail_status.services.llm_client import ConversationalAi, DeepseekClient, GeminiClient, LlmConfig


@pytest.fixture(autouse=True)
def dont_save_output(monkeypatch):
    monkeypatch.delenv("SAVE_AI_OUTPUTS", raising=False)


@pytest.fixture
def config(mock_api_keys, sample_llm_config):
    """テスト用のLlmConfig"""
    return LlmConfig(**sample_llm_config)


@pytest.fixture
def validation_error():
    class _Dummy(BaseModel):
        """ValidationErrorインスタンス作成用クラス"""

        x: int

    try:
        _Dummy(x="oops")
    except ValidationError as e:
        dummy_error = e

    return dummy_error


@pytest.fixture
def ai_class(monkeypatch):
    class DummyAi(ConversationalAi):
        @property
        def prompt_with_data(self): ...

        async def _call_api(self): ...

        def _extract_text(self, raw_response): ...

        def _get_validated_data(self, raw_response): ...

        def _create_token_stats(self, raw_response): ...

        async def _handle_exceptions(self, e, retry_count, max_retries): ...

    mock_call = AsyncMock(return_value="dummy_response")
    mock_extract = MagicMock(return_value="response_text")
    mock_validate = MagicMock(return_value={"validated": "yes"})
    mock_create_stats = MagicMock(return_value="dummy_stats")
    monkeypatch.setattr(DummyAi, "_call_api", mock_call)
    monkeypatch.setattr(DummyAi, "_extract_text", mock_extract)
    monkeypatch.setattr(DummyAi, "_get_validated_data", mock_validate)
    monkeypatch.setattr(DummyAi, "_create_token_stats", mock_create_stats)

    return DummyAi


class TestGenerate:
    @pytest.mark.asyncio
    async def test_success(self, ai_class, config):
        """テンプレートメソッド（_generate）のメイン処理成功ケース"""
        expected = {"validated": "yes"}, "dummy_stats"

        obj: ConversationalAi = ai_class(config)
        result = await obj._generate()

        obj._call_api.assert_called_once()
        obj._extract_text.assert_called_once_with("dummy_response")
        obj._get_validated_data.assert_called_once_with("dummy_response")
        obj._create_token_stats.assert_called_once_with("dummy_response")

        assert result == expected

    @pytest.mark.asyncio
    async def test_wrapper(self, monkeypatch, ai_class, config):
        """メイン処理メソッドのラッパーメソッド（generate）の正常テストケース"""
        mock_generate = AsyncMock(return_value="ai_result")
        monkeypatch.setattr(ai_class, "_generate", mock_generate)

        obj: ConversationalAi = ai_class(config)
        result = await obj.generate()

        mock_generate.assert_called_once()
        assert result == mock_generate.return_value

    @pytest.mark.asyncio
    async def test_validation_error(self, monkeypatch, ai_class, config, validation_error):
        """_generate()バリデーションエラー時のハンドリング・リトライ回数の結合テスト"""
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        monkeypatch.setattr(ai_class, "save_invalid_data", MagicMock())
        monkeypatch.setattr(ai_class, "_get_validated_data", MagicMock(side_effect=[validation_error] * 3))

        final_temperature = config.temperature + 0.2

        obj: ConversationalAi = ai_class(config)

        # インスタンス作成しメソッド束縛後にパッチ
        monkeypatch.setattr(ai_class, "validation_error", AsyncMock(wraps=obj.validation_error))

        with pytest.raises(ValidationError):
            await obj._generate()

        assert config.temperature == final_temperature
        assert obj.validation_error.call_count == 3
        obj.save_invalid_data.assert_called_once_with("response_text")


class TestGemini:


def test_deepseek_client_initialization(config):
    """DeepSeekクライアントの初期化テスト"""
    client = DeepseekClient(config)
    assert client.config.model == "deepseek-chat"
    assert client.config.temperature == 0.3
    assert client.config.prompt == "テスト用プロンプト"


def test_prompt_generation(config):
    """プロンプト生成テスト"""
    client = DeepseekClient(config)
    prompt = client.prompt_with_data

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
    from trail_status.services.types import ConditionSchemaAiList

    mock_validated_data = ConditionSchemaAiList(trail_condition_records=[])
    monkeypatch.setattr(client, "_get_validated_data", lambda x: mock_validated_data)
    monkeypatch.setattr(client, "save_sample_data", lambda x: None)

    validated_data, token_stats = await client.generate()

    assert isinstance(validated_data, ConditionSchemaAiList)
    assert len(validated_data.trail_condition_records) == 0
    assert token_stats.input_tokens == 100
    assert token_stats.pure_output_tokens == 50
