from __future__ import annotations

import asyncio
import logging
import os
import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from langsmith import traceable
from pydantic import BaseModel, Field, ValidationError, computed_field

from .llm_stats import TokenStats
from .types import ConditionSchemaAiList

logger = logging.getLogger(__name__)


# ヘルパー関数
def get_sample_dir() -> Path:
    """sampleディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "sample"


def get_prompts_dir() -> Path:
    """promptsディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "prompts"


class LlmConfig(BaseModel):
    site_prompt: str | None = Field(default="", description="サイト固有プロンプト")
    use_template: bool = Field(default=True, description="template.yamlを使用するか")
    model: str = Field(
        pattern=r"^(gemini|deepseek|gpt)-.+", default="gemini-flash-latest", description="使用するLLMモデル"
    )
    data: str = Field(description="解析するテキスト")
    temperature: float = Field(
        default=0.5, ge=0, le=2.0, description="生成ごとの揺らぎの幅（※ deepseek-reasonerでは無視される）"
    )
    thinking_budget: int = Field(default=10000, ge=-1, le=15000, description="Geminiの思考予算（トークン数）")
    prompt_filename: str | None = Field(default=None, description="プロンプトファイル名")
    allow_websearch: bool = Field(default=True, description="Gemini, OpenAIでWeb検索を許可するかどうか")

    @computed_field
    @property
    def full_prompt(self) -> str:
        """テンプレートとサイト固有プロンプトを結合"""
        parts = []
        if self.use_template:
            parts.append(self._load_template())
        if self.site_prompt:
            parts.append(self.site_prompt)
        return "\n\n".join(parts) if parts else ""

    @computed_field(repr=False)
    @property
    def api_key(self) -> str:
        """モデルに基づいてAPIキーを自動取得（遅延評価）"""
        if self.model.startswith("deepseek"):
            key = os.environ.get("DEEPSEEK_API_KEY")
            if not key:
                raise ValueError("環境変数 DEEPSEEK_API_KEY が設定されていません")
            return key
        elif self.model.startswith("gemini"):
            key = os.environ.get("GEMINI_API_KEY")
            if not key:
                raise ValueError("環境変数 GEMINI_API_KEY が設定されていません")
            return key
        elif self.model.startswith("gpt"):
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ValueError("環境変数 OPENAI_API_KEY が設定されていません")
            return key
        else:
            raise ValueError(f"サポートされていないモデル: {self.model}")

    # langsmith測定用
    @property
    def provider(self):
        if self.model.startswith("gemini"):
            return "google_genai"
        else:
            return "openai"

    @classmethod
    def from_file(cls, prompt_filename: str, data: str, **cli_overrides) -> LlmConfig:
        """
        プロンプトファイルから設定を読み込んでインスタンス作成

        Args:
            prompt_filename: プロンプトファイル名
            data: 解析するテキスト
            **cli_overrides: CLI引数による上書き設定

        Returns:
            LlmConfig: 設定がマージされたインスタンス
        """
        all_config = cls._load_site_config(prompt_filename)

        # None値を持つキーを完全に洗浄
        all_config = cls._to_safe_dict(all_config)
        site_config = all_config.get("config", {})
        site_config = cls._to_safe_dict(site_config)

        # CLI > promptファイル > デフォルト の優先度
        # Noneの場合はPydanticデフォルト値を使用するため、引数から除外
        kwargs = {
            "site_prompt": all_config.get("prompt", ""),
            "use_template": site_config.get("use_template", True),
            "data": data,
            "prompt_filename": prompt_filename,
        }

        # None以外の値のみ設定（Noneの場合はPydanticデフォルトを使用）
        model_value = cli_overrides.get("model") or site_config.get("model")
        if model_value:
            kwargs["model"] = model_value

        # temperature: 0.0対応（is not None チェック）
        temp_value = cli_overrides.get("temperature")
        if temp_value is None:
            temp_value = site_config.get("temperature")
        if temp_value is not None:
            kwargs["temperature"] = temp_value

        # thinking_budget: 0対応（通常0は無効値なので or 使用）
        budget_value = cli_overrides.get("thinking_budget") or site_config.get("thinking_budget")
        if budget_value:
            kwargs["thinking_budget"] = budget_value

        return cls(**kwargs)

    @staticmethod
    @lru_cache
    def _load_template(filename: str = "template.yaml") -> str:
        """
        template.yamlを読み込み辞書で返却

        Args:
            filename: テンプレートプロンプトファイル名（template.yaml）

        Returns:
            str: プロンプト文字列

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: プロンプトが設定されていない場合
        """
        template_dir = get_prompts_dir()
        template_path = template_dir / filename

        if not template_path.exists():
            raise FileNotFoundError(f"テンプレートファイルが見つかりません: {template_path}")

        prompt_dict = yaml.safe_load(template_path.read_text(encoding="utf-8"))

        if "prompt" not in prompt_dict:
            raise ValueError(f"テンプレートプロンプトが設定されていません: {template_path}")

        return prompt_dict["prompt"]

    @staticmethod
    def _load_site_config(filename: str) -> dict:
        """個別プロンプトファイルをファイル名から安全に読み込み辞書で返却
            ファイルがなければ作成をする

        Args:
            filename (str): YAMLファイル名（例：001_okutama_vc.yaml）

        Returns:
            dict: 取得したYAMLファイルの辞書 / 値がない場合: `{}`
        """
        prompts_dir = get_prompts_dir()
        prompt_path = prompts_dir / filename

        if not prompt_path.exists():
            logger.warning(f"サイト別プロンプトファイルが見つかりません: {prompt_path}")
            try:
                shutil.copy(prompts_dir / "example.yaml", prompt_path)
                logger.warning(f"プロンプトファイルを作成しました。ファイル名: {filename}")
            except Exception:
                logger.error("サイト別プロンプトファイルの作成に失敗。example.yamlを確認してください")
            return {}

        config_dict = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))

        if config_dict is None:
            logger.warning(f"サイト別プロンプトに記載がありません。ファイル名: {filename}")
            return {}

        return config_dict

    @staticmethod
    def _to_safe_dict(config_dict: dict) -> dict:
        """Noneを値に持つ辞書のキーを完全排除

        Args:
            config_dict (dict): キーはあるが値未設定の辞書（getメソッドでエラー）

        Returns:
            dict: 安全にgetできる辞書
        """
        if config_dict:
            config_dict = {k: v for k, v in config_dict.items() if v is not None}
        return config_dict

    def __str__(self) -> str:
        """デバッグ用に重要な情報を表示"""
        data_preview = self.data[:50] + "..." if len(self.data) > 50 else self.data

        return (
            f"LlmConfig("
            f"model={self.model!r}, temp={self.temperature}, prompt_len={len(self.full_prompt)}, "
            f"data_len={len(self.data)}, prompt_filename={self.prompt_filename!r}, "
            f"data_preview={data_preview!r}"
            f")"
        )


class ConversationalAi(ABC):
    MAX_RETRIES = 3

    def __init__(self, config: LlmConfig):
        self.model: str = config.model
        self.temperature: float = config.temperature
        self.prompt: str = config.full_prompt  # full_promptを使用
        self.data: str = config.data
        self.api_key: str = config.api_key
        self.thinking_budget: int = config.thinking_budget
        self.prompt_filename: str | None = config.prompt_filename
        self.provider: str | None = config.provider
        self.websearch: bool = config.allow_websearch
        self._config: LlmConfig | None = config

    async def generate(self) -> tuple[dict, TokenStats]:
        @traceable(
            run_type="llm",
            name=f"{self.prompt_filename}_{self.model.capitalize()}",
            metadata={
                "ls_provider": self.provider,
                "ls_model_name": self.model,
                "ls_temperature": self.temperature,
                "ls_max_tokens": self.thinking_budget,
            },
        )
        async def _run() -> tuple[ConditionSchemaAiList, TokenStats]:
            """LangSmithのデコレータを定義するためだけの関数内関数

            Returns:
                tuple[ConditionSchemaAiList, TokenStats]
            """
            for i in range(self.MAX_RETRIES):
                logger.info(f"{self.model}の応答を待っています。")
                logger.debug(f"LlmConfig詳細： \n{self._config}")
                logger.debug(f"APIキー: ...{self.api_key[-5:]}")

                try:
                    raw_response = await self._call_api()  # 各クライアントで実装されるAPI呼び出し
                    response_text = self._extract_text(raw_response)  # 各クライアントで実装されるテキスト抽出
                    validated_data = self._get_validated_data(raw_response)  # 共通のバリデーション
                    break
                except ValidationError as e:
                    await self.validation_error(e, i, self.MAX_RETRIES, response_text)
                except Exception as e:
                    await self._handle_exceptions(e, i, self.MAX_RETRIES)

            # AI出力の保存設定
            if os.getenv("SAVE_AI_OUTPUTS") in ["True", "true", "t"]:
                self.save_sample_data(response_text)
            stats = self._create_token_stats(raw_response)  # 共通のトークン統計作成関数

            logger.debug("ConversationalAiの処理終了")
            return validated_data, stats

        return await _run()

    @abstractmethod
    async def _call_api(self) -> Any: ...

    @abstractmethod
    def _extract_text(self, raw_response: Any) -> str: ...

    @abstractmethod
    def _get_validated_data(self, raw_response: Any) -> ConditionSchemaAiList: ...

    @abstractmethod
    def _create_token_stats(self, raw_response: Any) -> TokenStats: ...

    @abstractmethod
    async def _handle_exceptions(self, e: Exception, retry_count: int, max_retries: int) -> None: ...

    # サーバーエラーとバリデーションエラー時のみリトライ
    async def handle_server_error(self, e, i, max_retries):
        if i < max_retries - 1:
            logger.warning(f"{self.model}の計算資源が逼迫しているようです。{3 ** (i + 1)}秒後にリトライします。")
            await asyncio.sleep(3 ** (i + 1))
        else:
            logger.error(f"{self.model}は現在過負荷のようです。少し時間をおいて再実行する必要があります。")
            logger.error("実行を中止します。")
            raise e

    async def validation_error(self, e, i, max_retries, response_text) -> None:
        if i < max_retries - 1:
            logger.warning(f"{self.model}が構造化出力に失敗。")
            self.temperature += 0.1
            logger.warning(f"Temperatureを0.1上げてリトライします。更新後のTemperature: {self.temperature}")
            if self.temperature == 0.0:
                logger.warning(
                    "Temperature=0は毎回同じ出力（＝構造化失敗）となります。設定を0.1以上にすることを検討してください"
                )
            logger.warning(f"設定ファイル名:{self.prompt_filename!r}")
            logger.warning("3秒後にリトライします")
            await asyncio.sleep(3)
        else:
            logger.error(f"{self.model}が{max_retries}回構造化出力に失敗。LLMの設定を見直してください。")
            self.save_invalid_data(response_text)
            logger.error("実行を中止します。")
            raise e

    def handle_client_error(self, e: Exception):
        logger.error("エラー：APIレート制限。")
        logger.error("詳細はapp.logを確認してください。実行を中止します。")
        logger.error(f"詳細: {e}")
        raise e

    def handle_unexpected_error(self, e: Exception):
        logger.error("要約取得中に予期せぬエラー発生。詳細はapp.logを確認してください。")
        logger.error("実行を中止します。")
        logger.error(f"詳細: {e}")
        raise e

    def save_sample_data(self, response_text: str):
        # デバッグ用：サンプル出力を保存
        from datetime import datetime

        output_dir = get_sample_dir() / Path(self.prompt_filename or "").stem
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"{self.model}_{timestamp}.json"
        output_path.write_text(response_text, encoding="utf-8")

    def save_invalid_data(self, response_text: str):
        # エラー時の出力保存
        from datetime import datetime

        output_dir: Path = settings.BASE_DIR / "outputs"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_file = output_dir / f"validation_error_{self.model}_{self.prompt_filename}_{timestamp}.txt"
        error_file.write_text(response_text, encoding="utf-8")

        logger.error(f"{error_file}へ出力を保存しました。")


class DeepseekClient(ConversationalAi):
    from openai.types.chat import ChatCompletion

    @property
    def prompt_for_deepseek(self):
        STATEMENT = f"【重要】次の行から示す要請はこのPydanticモデルに合うJSONで出力してください: {ConditionSchemaAiList.model_json_schema()}\n"
        return STATEMENT + self.prompt + "\n\n\n" + self.data

    async def _call_api(self) -> ChatCompletion:
        from langsmith.wrappers import wrap_openai
        from openai import AsyncOpenAI

        client = wrap_openai(AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com"))

        response = await client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": "user", "content": self.prompt_for_deepseek}],
            response_format={"type": "json_object"},
            stream=False,
        )
        return response

    def _extract_text(self, raw_response: ChatCompletion) -> str:
        return raw_response.choices[0].message.content or ""

    def _get_validated_data(self, raw_response: ChatCompletion) -> ConditionSchemaAiList:
        return ConditionSchemaAiList.model_validate_json(self._extract_text(raw_response))

    def _create_token_stats(self, raw_response: ChatCompletion) -> TokenStats:
        # Noneチェック
        if raw_response.usage:
            prompt_tokens = raw_response.usage.prompt_tokens
            completion_tokens = raw_response.usage.completion_tokens
            thoughts_tokens = getattr(raw_response.usage.completion_tokens_details, "reasoning_tokens", 0) or 0
            # 純粋なoutput_tokensを計算
            output_tokens = completion_tokens - thoughts_tokens

        else:
            logger.warning("Deepseek API response did not include usage metadata.")
            prompt_tokens = 0
            thoughts_tokens = 0
            output_tokens = 0

        stats = TokenStats(
            prompt_tokens,
            thoughts_tokens,
            output_tokens,
            len(self.prompt_for_deepseek),
            len(self._extract_text(raw_response)),
            self.model,
        )
        return stats

    async def _handle_exceptions(self, e: Exception, retry_count: int, max_retries: int) -> None:
        if any(code in str(e) for code in ["500", "502", "503"]):
            await self.handle_server_error(retry_count, max_retries)
        elif "429" in str(e):
            logger.error("APIレート制限。しばらく経ってから再実行してください。")
            raise e
        elif "401" in str(e):
            logger.error("エラー：APIキーが誤っているか、入力されていません。")
            logger.error(f"実行を中止します。詳細：{e}")
            raise e
        elif "402" in str(e):
            logger.error("残高が不足しているようです。アカウントを確認してください。")
            logger.error(f"実行を中止します。詳細：{e}")
            raise e
        elif "422" in str(e):
            logger.error("リクエストに無効なパラメータが含まれています。設定を見直してください。")
            logger.error(f"実行を中止します。詳細：{e}")
            raise e
        else:
            self.handle_unexpected_error(e)


class GeminiClient(ConversationalAi):
    from google.genai.types import GenerateContentResponse

    @property
    def prompt_for_gemini(self):
        return self.prompt + "\n\n\n" + self.data

    async def _call_api(self) -> GenerateContentResponse:
        from google import genai
        from google.genai import types
        from langsmith.wrappers import wrap_gemini

        # api_key引数なしでも、環境変数"GEMNI_API_KEY"の値を勝手に参照するが、可読性のため代入
        client = wrap_gemini(
            genai.Client(http_options=types.HttpOptions(timeout=120 * 1000))  # 2分
        )

        # 検索許可設定
        search_tool = types.Tool(google_search=types.GoogleSearch()) if self.websearch else None

        response = await client.aio.models.generate_content(  # リクエスト
            model=self.model,
            contents=self.prompt_for_gemini,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                response_mime_type="application/json",  # 構造化出力
                response_json_schema=ConditionSchemaAiList.model_json_schema(),
                thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),
                tools=[search_tool],
            ),
        )
        return response

    def _extract_text(self, raw_response: GenerateContentResponse) -> str:
        return raw_response.text

    @traceable
    def _get_validated_data(self, raw_response: GenerateContentResponse) -> ConditionSchemaAiList:
        """AI出力データのバリデーション"""
        try:
            validated_data = ConditionSchemaAiList.model_validate_json(self._extract_text(raw_response))
            logger.info(f"{self.model}が構造化出力に成功")
        except ValidationError as e:
            raise e
        return validated_data

    async def _handle_exceptions(self, e: Exception, retry_count: int, max_retries: int) -> None:
        from google.genai.errors import ClientError, ServerError

        if isinstance(e, ServerError):
            await self.handle_server_error(retry_count, max_retries)
        elif isinstance(e, ClientError):
            self.handle_client_error(e)
        else:
            self.handle_unexpected_error(e)

    def _create_token_stats(self, raw_response: GenerateContentResponse) -> TokenStats:
        for part in raw_response.candidates[0].content.parts:
            if not part.text:
                continue
            elif part.thought:
                logger.debug("## **Thoughts summary:**")
                logger.debug(part.text)
            else:
                logger.debug("## **Answer:**")
                logger.debug(part.text)

        # Noneチェック
        if raw_response.usage_metadata:
            prompt_tokens = raw_response.usage_metadata.prompt_token_count
            thoughts_tokens = getattr(raw_response.usage_metadata, "thoughts_token_count", 0) or 0
            output_tokens = raw_response.usage_metadata.candidates_token_count
        else:
            logger.warning("Gemini API response did not include usage metadata.")
            prompt_tokens = 0
            thoughts_tokens = 0
            output_tokens = 0

        stats = TokenStats(
            prompt_tokens,
            thoughts_tokens,
            output_tokens,
            len(self.prompt),
            len(raw_response.text),
            self.model,
        )
        return stats


class GptClient(ConversationalAi):
    from openai.types.responses import ParsedResponse

    @property
    def prompt_for_gpt(self):
        input = [
            {
                "role": "system",
                "content": f"{self.prompt}",
            },
            {"role": "user", "content": f"{self.data}"},
        ]
        return input

    async def _call_api(self) -> ParsedResponse[ConditionSchemaAiList]:
        from langsmith.wrappers import wrap_openai
        from openai import AsyncOpenAI

        client = wrap_openai(AsyncOpenAI())
        # 検索許可設定
        search_tool = (
            {"type": "web_search", "user_location": {"city": "Tokyo", "type": "approximate"}}
            if self.websearch
            else None
        )

        response = await client.responses.parse(
            model=self.model,
            tools=[search_tool],
            input=self.prompt_for_gpt,
            text_format=ConditionSchemaAiList,
        )
        return response

    def _extract_text(self, raw_response: ParsedResponse[ConditionSchemaAiList]) -> str:
        return raw_response.output_parsed.model_dump_json()

    def _get_validated_data(self, raw_response: ParsedResponse[ConditionSchemaAiList]) -> ConditionSchemaAiList:
        return raw_response.output_parsed

    def _create_token_stats(self, raw_response: ParsedResponse[ConditionSchemaAiList]) -> TokenStats:
        # Noneチェック
        if raw_response.usage:
            input_tokens = raw_response.usage.input_tokens
            output_tokens = raw_response.usage.output_tokens
            thoughts_tokens = getattr(raw_response.usage.output_tokens_details, "reasoning_tokens", 0) or 0
            # 純粋なoutput_tokensを計算
            pure_output_tokens = output_tokens - thoughts_tokens
        else:
            logger.warning("GPT API response did not include usage metadata.")
            input_tokens = 0
            thoughts_tokens = 0
            pure_output_tokens = 0

        stats = TokenStats(
            input_tokens,
            thoughts_tokens,
            pure_output_tokens,
            len(self.prompt + self.data),
            -1,
            self.model,
        )
        return stats

    async def _handle_exceptions(self, e: Exception, retry_count: int, max_retries: int) -> None:
        if any(code in str(e) for code in ["500", "502", "503"]):
            await self.handle_server_error(retry_count, max_retries)
        elif "429" in str(e):
            logger.error("APIレート制限。しばらく経ってから再実行してください。")
            raise e
        elif "401" in str(e):
            logger.error("エラー：APIキーが誤っているか、入力されていません。")
            logger.error(f"実行を中止します。詳細：{e}")
            raise e
        elif "402" in str(e):
            logger.error("残高が不足しているようです。アカウントを確認してください。")
            logger.error(f"実行を中止します。詳細：{e}")
            raise e
        elif "422" in str(e):
            logger.error("リクエストに無効なパラメータが含まれています。設定を見直してください。")
            logger.error(f"実行を中止します。詳細：{e}")
            raise e
        else:
            self.handle_unexpected_error(e)
