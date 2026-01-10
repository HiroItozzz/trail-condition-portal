from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

import yaml
from django.conf import settings
from langsmith import traceable
from pydantic import BaseModel, Field, ValidationError, computed_field

from .llm_stats import TokenStats
from .schema import TrailConditionSchemaList

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
    model: str = Field(pattern=r"^(gemini|deepseek)-.+", default="deepseek-reasoner", description="使用するLLMモデル")
    data: str = Field(description="解析するテキスト")
    temperature: float = Field(
        default=0.0, ge=0, le=2.0, description="生成ごとの揺らぎの幅（※ deepseek-reasonerでは無視される）"
    )
    thinking_budget: int = Field(default=5000, ge=-1, le=15000, description="Geminiの思考予算（トークン数）")
    prompt_filename: str | None = Field(default=None, description="LLMエラー処理での識別用ファイルネーム")

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
        else:
            raise ValueError(f"サポートされていないモデル: {self.model}")

    @property
    def provider(self):
        if self.model.startswith("deepseek"):
            return "openai"
        elif self.model.startswith("gemini"):
            return "google_genai"

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
        else:
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

        Args:
            filename (str): YAMLファイル名（例：001_okutama_vc.yaml）

        Returns:
            dict: 取得したYAMLファイルの辞書 / 値がない場合: `{}`
        """
        prompts_dir = get_prompts_dir()
        prompt_path = prompts_dir / filename

        if not prompt_path.exists():
            logger.warning(f"サイト別プロンプトファイルが見つかりません: {prompt_path}")
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
    def __init__(self, config: LlmConfig):
        self.model: str = config.model
        self.temperature: float = config.temperature
        self.prompt: str = config.full_prompt  # full_promptを使用
        self.data: str = config.data
        self.api_key: str = config.api_key
        self.thinking_budget: int = config.thinking_budget
        self.prompt_filename: str | None = config.prompt_filename
        self.provider: str | None = config.provider
        self._config: LlmConfig | None = config

    @abstractmethod
    async def generate(self) -> tuple[dict, TokenStats]:
        pass

    # サーバーエラーとバリデーションエラー時のみリトライ
    async def handle_server_error(self, i, max_retries):
        if i < max_retries - 1:
            logger.warning(f"{self.model}の計算資源が逼迫しているようです。{3 ** (i + 1)}秒後にリトライします。")
            await asyncio.sleep(3 ** (i + 1))
        else:
            logger.error(f"{self.model}は現在過負荷のようです。少し時間をおいて再実行する必要があります。")
            logger.error("実行を中止します。")
            raise

    async def validation_error(self, i, max_retries, response_text):
        if i < max_retries - 1:
            logger.warning(f"{self.model}が構造化出力に失敗。")
            if self.temperature == 0:
                self.temperature += 0.1
                logger.warning(f"Temperatureを0.1上げてリトライします。更新後のTemperature: {self.temperature}")
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
            raise

    def handle_client_error(self, e: Exception):
        logger.error("エラー：APIレート制限。")
        logger.error("詳細はapp.logを確認してください。実行を中止します。")
        logger.error(f"詳細: {e}")
        raise

    def handle_unexpected_error(self, e: Exception):
        logger.error("要約取得中に予期せぬエラー発生。詳細はapp.logを確認してください。")
        logger.error("実行を中止します。")
        logger.error(f"詳細: {e}")
        raise

    @traceable
    def validate_response(self, response_text):
        # デバッグ用：サンプル出力を保存
        sample_path = get_sample_dir() / f"{self.model}_sample.json"
        sample_path.write_text(response_text, encoding="utf-8")

        try:
            validated_data = TrailConditionSchemaList.model_validate_json(response_text)
            logger.info(f"{self.model}が構造化出力に成功")
        except ValidationError as e:
            raise e
        return validated_data

    def save_invalid_data(self, response_text):
        # エラー時の出力保存
        from datetime import datetime

        output_dir = settings.BASE_DIR / "outputs"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_file = output_dir / f"validation_error_{self.model}_{timestamp}.txt"
        error_file.write_text(response_text, encoding="utf-8")

        logger.error(f"{error_file}へ出力を保存しました。")


class DeepseekClient(ConversationalAi):
    @property
    def prompt_for_deepseek(self):
        STATEMENT = f"【重要】次の行から示す要請はこのPydanticモデルに合うJSONで出力してください: {TrailConditionSchemaList.model_json_schema()}\n"
        return STATEMENT + self.prompt + "\n\n\n" + self.data

    async def generate(self) -> tuple[TrailConditionSchemaList, TokenStats]:
        from openai import AsyncOpenAI

        @traceable(
            run_type="llm",
            name="Trail_Analysis_Deepseek",
            metadata={
                "ls_provider": self.provider,
                "ls_model_name": self.model,
                "ls_temperature": self.temperature,
                "ls_max_tokens": self.thinking_budget,
            },
        )
        async def _run(_: str) -> tuple[TrailConditionSchemaList, TokenStats]:
            """LangSmithのデコレータを定義するためだけのネスト関数

            Args:
                _ (str): LangSmithトレースのためのプロンプト入力

            Returns:
                tuple[TrailConditionSchemaList, TokenStats]
            """
            logger.info(f"{self.model}の応答を待っています。")
            logger.debug(f"LlmConfig詳細： \n{self._config}")
            logger.debug(f"APIキー: ...{self.api_key[-5:]}")

            client = AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

            max_retries = 3
            for i in range(max_retries):
                try:
                    response = await client.chat.completions.create(
                        model=self.model,
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": self.prompt_for_deepseek}],
                        response_format={"type": "json_object"},
                        stream=False,
                    )
                    generated_text = response.choices[0].message.content or ""
                    validated_data = self.validate_response(generated_text)
                    break
                except ValidationError:
                    await self.validation_error(i, max_retries, generated_text)
                except Exception as e:
                    # https://api-docs.deepseek.com/quick_start/error_codes
                    if any(code in str(e) for code in ["500", "502", "503"]):
                        await self.handle_server_error(i, max_retries)
                    elif "429" in str(e):
                        logger.error("APIレート制限。しばらく経ってから再実行してください。")
                        raise
                    elif "401" in str(e):
                        logger.error("エラー：APIキーが誤っているか、入力されていません。")
                        logger.error(f"実行を中止します。詳細：{e}")
                        raise
                    elif "402" in str(e):
                        logger.error("残高が不足しているようです。アカウントを確認してください。")
                        logger.error(f"実行を中止します。詳細：{e}")
                        raise
                    elif "422" in str(e):
                        logger.error("リクエストに無効なパラメータが含まれています。設定を見直してください。")
                        logger.error(f"実行を中止します。詳細：{e}")
                        raise
                    else:
                        self.handle_unexpected_error(e)

            # 安全なNoneチェックを追加
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                thoughts_tokens = getattr(response.usage.completion_tokens_details, "reasoning_tokens", 0) or 0
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
                len(generated_text),
                self.model,
            )

            logger.debug("DeepseekClientの処理終了")
            return validated_data, stats

        return await _run(self.prompt_for_deepseek)


class GeminiClient(ConversationalAi):
    @property
    def prompt_for_gemini(self):
        return self.prompt + "\n\n\n" + self.data

    async def generate(self) -> tuple[TrailConditionSchemaList, TokenStats]:
        from google import genai
        from google.genai import types
        from google.genai.errors import ClientError, ServerError

        @traceable(
            run_type="llm",
            name="Trail_Analysis_Gemini",
            metadata={
                "ls_provider": self.provider,
                "ls_model_name": self.model,
                "ls_temperature": self.temperature,
                "ls_max_tokens": self.thinking_budget,
            },
        )
        async def _run(_: str) -> tuple[TrailConditionSchemaList, TokenStats]:
            """LangSmithのデコレータを定義するためだけのネスト関数

            Args:
                _ (str): LangSmithトレースのためのプロンプト入力

            Returns:
                tuple[TrailConditionSchemaList, TokenStats]
            """
            logger.info(f"{self.model}の応答を待っています。")
            logger.debug(f"LlmConfig詳細： \n{self._config}")
            logger.debug(f"APIキー: ...{self.api_key[-5:]}")

            # api_key引数なしでも、環境変数"GEMNI_API_KEY"の値を勝手に参照するが、可読性のため代入
            client = genai.Client()

            max_retries = 3
            for i in range(max_retries):
                try:
                    response = await client.aio.models.generate_content(  # リクエスト
                        model=self.model,
                        contents=self.prompt_for_gemini,
                        config=types.GenerateContentConfig(
                            temperature=self.temperature,
                            response_mime_type="application/json",  # 構造化出力
                            response_json_schema=TrailConditionSchemaList.model_json_schema(),
                            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),
                        ),
                    )
                    validated_data = self.validate_response(response.text)
                    break
                except ValidationError:
                    await self.validation_error(i, max_retries, response.text)
                except ServerError:
                    await self.handle_server_error(i, max_retries)
                except ClientError as e:
                    self.handle_client_error(e)
                except Exception as e:
                    self.handle_unexpected_error(e)

            for part in response.candidates[0].content.parts:
                if not part.text:
                    continue
                elif part.thought:
                    logger.debug("## **Thoughts summary:**")
                    logger.debug(part.text)
                else:
                    logger.debug("## **Answer:**")
                    logger.debug(part.text)

            # 安全なNoneチェックを追加
            if response.usage_metadata:
                prompt_tokens = response.usage_metadata.prompt_token_count
                thoughts_tokens = getattr(response.usage_metadata, "thoughts_token_count", 0) or 0
                output_tokens = response.usage_metadata.candidates_token_count
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
                len(response.text),
                self.model,
            )

            logger.debug("GeminiClientの処理終了")

            return validated_data, stats

        return await _run(self.prompt_for_gemini)


# テスト用コードは削除されました
# テスト実行は以下のコマンドを使用してください:
# docker compose exec web uv run manage.py test_llm
#
# 使用例:
# config = LlmConfig.from_site("okutama", data=scraped_data, model="deepseek-reasoner")
# client = DeepseekClient(config)  # api_keyは自動取得
# data, stats = await client.generate()
