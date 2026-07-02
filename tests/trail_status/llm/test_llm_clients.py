"""
LLMクライアント（DeepSeek/Gemini）のテスト
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest
from google import genai
from google.genai.errors import ClientError, ServerError
from google.genai.models import AsyncModels
from openai.resources.chat.completions import AsyncCompletions
from openai.resources.responses import AsyncResponses
from pydantic import BaseModel, ValidationError

from trail_status.services.llm_client import ConversationalAi, DeepseekClient, GeminiClient, GptClient, LlmConfig
from trail_status.services.llm_stats import TokenStats
from trail_status.services.types import ConditionSchemaAiList, LlmModel


@pytest.fixture(autouse=True)
def mock_api_keys(monkeypatch):
    """API キーをモック設定（全テスト共通）"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


@pytest.fixture
def deepseek_config(mock_api_keys, llm_config_factory):
    """テスト用のLlmConfig"""
    config_dict = llm_config_factory(LlmModel.DEEPSEEK_CHAT)
    return LlmConfig(**config_dict)


@pytest.fixture
def gemini_config(mock_api_keys, llm_config_factory):
    """テスト用のLlmConfig"""
    config_dict = llm_config_factory(LlmModel.GEMINI_3_1_FLASH_LITE)
    return LlmConfig(**config_dict)


@pytest.fixture
def gpt_config(mock_api_keys, llm_config_factory):
    """テスト用のLlmConfig"""
    config_dict = llm_config_factory(LlmModel.GPT_5_NANO)
    return LlmConfig(**config_dict)


@pytest.fixture
def ai_class(monkeypatch):
    class DummyAi(ConversationalAi):
        """共通メソッドテスト用の汎用AIモック"""

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


class TestGenerate:
    @pytest.mark.asyncio
    async def test_success(self, ai_class, llm_config_factory):
        """テンプレートメソッド（_generate）のメイン処理成功ケース"""
        expected = {"validated": "yes"}, "dummy_stats"

        llm_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        obj: ConversationalAi = ai_class(llm_config)
        result = await obj._generate()

        obj._call_api.assert_called_once()
        obj._extract_text.assert_called_once_with("dummy_response")
        obj._get_validated_data.assert_called_once_with("dummy_response")
        obj._create_token_stats.assert_called_once_with("dummy_response")

        assert result == expected

    @pytest.mark.asyncio
    async def test_wrapper(self, monkeypatch, ai_class, llm_config_factory):
        """メイン処理メソッドのラッパーメソッド（generate）の正常テストケース"""
        mock_generate = AsyncMock(return_value="ai_result")
        monkeypatch.setattr(ai_class, "_generate", mock_generate)

        llm_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        obj: ConversationalAi = ai_class(llm_config)
        result = await obj.generate()

        mock_generate.assert_called_once()
        assert result == mock_generate.return_value

    @pytest.mark.asyncio
    async def test_validation_error(self, monkeypatch, ai_class, llm_config_factory, validation_error):
        """_generate()バリデーションエラー時のハンドリング・リトライ回数の結合テスト"""
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        monkeypatch.setattr(ai_class, "save_invalid_data", MagicMock())
        monkeypatch.setattr(
            ai_class, "_get_validated_data", MagicMock(side_effect=[validation_error] * ai_class.MAX_RETRIES)
        )

        llm_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        obj: ConversationalAi = ai_class(llm_config)

        # インスタンス作成しメソッド束縛後にパッチ
        monkeypatch.setattr(ai_class, "validation_error", AsyncMock(wraps=obj.validation_error))

        final_temperature = llm_config.temperature + 0.2

        with pytest.raises(ValidationError):
            await obj._generate()

        assert llm_config.temperature == final_temperature
        assert obj.validation_error.call_count == obj.MAX_RETRIES
        obj.save_invalid_data.assert_called_once_with("response_text")


class TestGemini:
    def test_prompt_generation(self, llm_config_factory):
        """プロパティにおける指示とデータの結合の挙動"""
        gemini_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        client = GeminiClient(gemini_config)
        result = client.prompt_with_data

        assert gemini_config.prompt in result
        assert gemini_config.data in result

    @pytest.mark.asyncio
    async def test_call_api(self, monkeypatch, llm_config_factory, mock_gemini_response):
        """API呼び出しを行うメソッドの挙動"""
        gemini_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)

        monkeypatch.setattr(genai, "Client", MagicMock(wraps=genai.Client))
        monkeypatch.setattr(AsyncModels, "generate_content", AsyncMock(return_value=mock_gemini_response))

        client = GeminiClient(gemini_config)
        result = await client._call_api()

        genai.Client.assert_called_once()
        AsyncModels.generate_content.assert_called_once()
        assert result == mock_gemini_response

    def test_extract_text(self, llm_config_factory, mock_gemini_response):
        """生レスポンスから(JSON)テキスト抽出のテスト"""
        gemini_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        client = GeminiClient(gemini_config)
        result = client._extract_text(mock_gemini_response)

        assert result == (mock_gemini_response.text or "")

    def test_validation(self, monkeypatch, llm_config_factory, mock_gemini_response):
        """生レスポンスのバリデーションの挙動"""
        gemini_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)

        monkeypatch.setattr(ConditionSchemaAiList, "model_validate_json", MagicMock(return_value="validated"))
        monkeypatch.setattr(GeminiClient, "_extract_text", MagicMock(return_value=mock_gemini_response.text))

        client = GeminiClient(gemini_config)
        result = client._get_validated_data(mock_gemini_response)

        GeminiClient._extract_text.assert_called_once_with(mock_gemini_response)
        ConditionSchemaAiList.model_validate_json.assert_called_once_with(mock_gemini_response.text)
        assert result == "validated"

    def test_get_validated_data_error_raised(
        self, monkeypatch, llm_config_factory, mock_gemini_response, validation_error
    ):
        """生レスポンスのバリデーションエラー時の挙動（リレイズ）"""
        gemini_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)

        monkeypatch.setattr(ConditionSchemaAiList, "model_validate_json", MagicMock(side_effect=validation_error))
        monkeypatch.setattr(GeminiClient, "_extract_text", MagicMock(return_value=mock_gemini_response.text))

        client = GeminiClient(gemini_config)
        with pytest.raises(ValidationError):
            client._get_validated_data(mock_gemini_response)

        ConditionSchemaAiList.model_validate_json.assert_called_once_with(mock_gemini_response.text)

    def test_create_token_stats(self, llm_config_factory, mock_gemini_response):
        """トークン計算の挙動"""
        gemini_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)

        client = GeminiClient(gemini_config)
        result = client._create_token_stats(mock_gemini_response)

        assert isinstance(result, TokenStats)

    @pytest.mark.parametrize(
        "error, expected_method,call_count",
        [
            (ServerError(500, {"error": {"message": "server error"}}), "handle_server_error", 3),
        ],
    )
    @pytest.mark.asyncio
    async def test_server_error(self, monkeypatch, llm_config_factory, error, expected_method, call_count):
        """Geminiサーバーエラー時の挙動（リトライあり）"""
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        monkeypatch.setattr(GeminiClient, "_call_api", AsyncMock(side_effect=[error] * GeminiClient.MAX_RETRIES))

        llm_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        obj = GeminiClient(llm_config)

        # インスタンス作成しメソッド束縛後にパッチ
        monkeypatch.setattr(obj, expected_method, AsyncMock(wraps=getattr(obj, expected_method)))

        with pytest.raises(type(error)):
            await obj._generate()

        assert getattr(obj, expected_method).call_count == call_count

    @pytest.mark.parametrize(
        "error, expected_method,call_count",
        [
            (ClientError(400, {"error": {"message": "client error"}}), "handle_client_error", 1),
        ],
    )
    @pytest.mark.asyncio
    async def test_client_error(self, monkeypatch, llm_config_factory, error, expected_method, call_count):
        """Geminiクライアントエラー時の挙動（リトライなし）"""
        monkeypatch.setattr(GeminiClient, "_call_api", MagicMock(side_effect=[error] * GeminiClient.MAX_RETRIES))

        llm_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        obj = GeminiClient(llm_config)

        # インスタンス作成しメソッド束縛後にパッチ
        monkeypatch.setattr(obj, expected_method, MagicMock(wraps=getattr(obj, expected_method)))

        with pytest.raises(type(error)):
            await obj._generate()

        assert getattr(obj, expected_method).call_count == call_count

    @pytest.mark.parametrize(
        "error, expected_method",
        [
            (Exception, "handle_unexpected_error"),
        ],
    )
    @pytest.mark.asyncio
    async def test_unexpected_error(self, monkeypatch, llm_config_factory, error, expected_method):
        """Gemini予期せぬエラー時の挙動（リトライなし）"""
        monkeypatch.setattr(GeminiClient, "_call_api", AsyncMock(side_effect=[error] * GeminiClient.MAX_RETRIES))

        llm_config = llm_config_factory(LlmModel.GEMINI_3_FLASH_PREVIEW)
        obj = GeminiClient(llm_config)

        # インスタンス作成しメソッド束縛後にパッチ
        monkeypatch.setattr(obj, expected_method, MagicMock(wraps=getattr(obj, expected_method)))

        with pytest.raises(error):
            await obj._generate()

        getattr(obj, expected_method).assert_called_once()


class TestGpt:
    def test_prompt_generation(self, llm_config_factory):
        """プロパティにおける指示とデータの結合の挙動"""
        gpt_config = llm_config_factory(LlmModel.GPT_5_NANO)
        client = GptClient(gpt_config)

        result = client.prompt_with_data
        system_prompt, user_prompt = result

        assert gpt_config.prompt in system_prompt["content"]
        assert gpt_config.data in user_prompt["content"]

    @pytest.mark.asyncio
    async def test_call_api(self, monkeypatch, llm_config_factory, mock_openai_response):
        """API呼び出しを行うメソッドの挙動"""
        gpt_config = llm_config_factory(LlmModel.GPT_5_NANO)

        monkeypatch.setattr(openai, "AsyncOpenAI", MagicMock(wraps=openai.AsyncOpenAI))
        monkeypatch.setattr(AsyncResponses, "parse", AsyncMock(return_value=mock_openai_response))

        client = GptClient(gpt_config)
        result = await client._call_api()

        openai.AsyncOpenAI.assert_called_once()
        AsyncResponses.parse.assert_called_once()
        assert result == mock_openai_response

    def test_create_token_stats(self, llm_config_factory, mock_openai_response):
        """トークン計算の挙動"""
        gpt_config = llm_config_factory(LlmModel.GPT_5_NANO)

        client = GptClient(gpt_config)
        result = client._create_token_stats(mock_openai_response)

        assert isinstance(result, TokenStats)


class TestDeepseek:
    def test_prompt_generation(self, llm_config_factory):
        """プロパティにおける指示とデータの結合の挙動"""
        deepseek_config = llm_config_factory(LlmModel.DEEPSEEK_CHAT)
        client = DeepseekClient(deepseek_config)

        result = client.prompt_with_data

        assert deepseek_config.prompt in result
        assert deepseek_config.data in result

    @pytest.mark.asyncio
    async def test_call_api(self, monkeypatch, llm_config_factory, mock_openai_response):
        """API呼び出しを行うメソッドの挙動"""
        deepseek_config = llm_config_factory(LlmModel.DEEPSEEK_CHAT)

        monkeypatch.setattr(openai, "AsyncOpenAI", MagicMock(wraps=openai.AsyncOpenAI))
        monkeypatch.setattr(AsyncCompletions, "create", AsyncMock(return_value=mock_openai_response))

        client = DeepseekClient(deepseek_config)
        result = await client._call_api()

        openai.AsyncOpenAI.assert_called_once()
        AsyncCompletions.create.assert_called_once()
        assert result == mock_openai_response

    def test_create_token_stats(self, llm_config_factory, mock_openai_response):
        """トークン計算の挙動"""
        deepseek_config = llm_config_factory(LlmModel.DEEPSEEK_CHAT)

        client = DeepseekClient(deepseek_config)
        result = client._create_token_stats(mock_openai_response)

        assert isinstance(result, TokenStats)


def test_prompt_generation(llm_config_factory):
    """プロンプト生成テスト"""
    llm_config = llm_config_factory(LlmModel.DEEPSEEK_CHAT)
    client = DeepseekClient(llm_config)
    prompt = client.prompt_with_data

    # JSON Schema指示が含まれているかチェック
    assert "Pydanticモデル" in prompt
    assert "テスト用プロンプト" in prompt
    assert "テスト用データ" in prompt


@pytest.mark.asyncio
async def test_deepseek_generate_success(llm_config_factory, monkeypatch, mock_openai_response):
    """DeepSeek API呼び出し成功テスト（モック使用）"""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

    # openai.AsyncOpenAI をモック（メソッド内でインポートされるため）
    mock_openai_class = MagicMock(return_value=mock_client)
    monkeypatch.setattr("openai.AsyncOpenAI", mock_openai_class)

    llm_config = llm_config_factory(LlmModel.DEEPSEEK_CHAT)
    client = DeepseekClient(llm_config)

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
