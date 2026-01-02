import asyncio
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path

import yaml
from django.conf import settings
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, computed_field

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
    site_prompt: str = Field(default="", description="サイト固有プロンプト")
    use_template: bool = Field(default=True, description="template.yamlを使用するか")
    model: str = Field(pattern=r"^(gemini|deepseek)-.+", default="deepseek-chat", description="使用するLLMモデル")
    data: str = Field(description="解析するテキスト")
    temperature: float = Field(default=0.3, ge=0, le=2.0, description="生成ごとの揺らぎの幅")
    thinking_budget: int = Field(default=5000, ge=-1, le=15000, description="Geminiの思考予算（トークン数）")

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

    @computed_field
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

    @staticmethod
    def load_prompt(filename: str) -> str:
        """
        プロンプトファイルを読み込み

        Args:
            filename: プロンプトファイル名（例：001_okutama_vc.yaml）

        Returns:
            str: プロンプト文字列

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: プロンプトが設定されていない場合
        """
        prompts_dir = get_prompts_dir()
        prompt_path = prompts_dir / filename

        if not prompt_path.exists():
            raise FileNotFoundError(f"プロンプトファイルが見つかりません: {prompt_path}")

        config = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))

        if "prompt" not in config:
            raise ValueError(f"プロンプトが設定されていません: {prompt_path}")

        return config["prompt"]

    
    @staticmethod
    def _load_template() -> str:
        """template.yamlを読み込み"""
        return LlmConfig.load_prompt("template.yaml")


class ConversationalAi(ABC):
    def __init__(self, config: LlmConfig):
        self.model: str = config.model
        self.temperature: float = config.temperature
        self.prompt: str = config.full_prompt  # full_promptを使用
        self.data: str = config.data
        self.api_key: str = config.api_key
        self.thinking_budget: int = config.thinking_budget

    @abstractmethod
    async def generate(self) -> tuple[dict, TokenStats]:
        pass

    async def handle_server_error(self, i, max_retries):
        if i < max_retries - 1:
            logger.warning(f"deepseekの計算資源が逼迫しているようです。{5 * (i + 1)}秒後にリトライします。")
            await asyncio.sleep(5 * (i + 1))
        else:
            logger.warning("deepseekは現在過負荷のようです。少し時間をおいて再実行する必要があります。")
            logger.warning("実行を中止します。")
            raise

    def handle_client_error(self, e: Exception):
        logger.error("エラー：APIレート制限。")
        logger.error("詳細はapp.logを確認してください。実行を中止します。")
        logger.info(f"詳細: {e}")
        raise

    def handle_unexpected_error(self, e: Exception):
        logger.error("要約取得中に予期せぬエラー発生。詳細はapp.logを確認してください。")
        logger.error("実行を中止します。")
        logger.info(f"詳細: {e}")
        raise

    def check_response(self, response_text):
        # デバッグ用：サンプル出力を保存
        sample_path = get_sample_dir() / f"{self.model}_sample.json"
        sample_path.write_text(response_text, encoding="utf-8")

        try:
            validated_data = TrailConditionSchemaList.model_validate_json(response_text)
            dict_validated = validated_data.model_dump()
            logger.warning(f"{self.model}が構造化出力に成功")
        except Exception:
            logger.error(f"{self.model}が構造化出力に失敗。")

            # エラー時の出力保存
            output_dir = settings.BASE_DIR / "outputs"
            output_dir.mkdir(exist_ok=True)
            error_file = output_dir / "__summary.txt"
            error_file.write_text(response_text, encoding="utf-8")

            logger.error(f"{error_file}へ出力を保存しました。")
            raise

        return dict_validated


class DeepseekClient(ConversationalAi):
    @property
    def full_prompt(self):
        STATEMENT = f"【重要】次の行から示す要請はこのPydanticモデルに合うJSONで出力してください: {TrailConditionSchemaList.model_json_schema()}\n"
        return STATEMENT + self.prompt + self.data

    async def generate(self) -> tuple[dict, TokenStats]:
        logger.warning("Deepseekからの応答を待っています。")
        logger.debug(f"APIリクエスト中。APIキー: ...{self.api_key[-5:]}")

        client = AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

        max_retries = 3
        for i in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": self.full_prompt}],
                    response_format={"type": "json_object"},
                    stream=False,
                )
                break
            except Exception as e:
                # https://api-docs.deepseek.com/quick_start/error_codes
                if any(code in str(e) for code in ["500", "502", "503"]):
                    await super().handle_server_error(i, max_retries)
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
                    super().handle_unexpected_error(e)

        generated_text = response.choices[0].message.content
        data = super().check_response(generated_text)

        # 実際に出力されたテキストに基づく出力トークンを計算
        thoughts_tokens = getattr(response.usage.completion_tokens_details, "reasoning_tokens", 0)
        output_tokens = response.usage.completion_tokens - thoughts_tokens

        stats = TokenStats(
            response.usage.prompt_tokens,
            thoughts_tokens,
            output_tokens,
            len(self.full_prompt),
            len(generated_text),
            self.model,
        )

        return data, stats


class GeminiClient(ConversationalAi):
    async def generate(self):
        from google import genai
        from google.genai import types
        from google.genai.errors import ClientError, ServerError

        logger.warning("Geminiからの応答を待っています。")
        logger.debug(f"APIリクエスト中。APIキー: ...{self.api_key[-5:]}")

        # api_key引数なしでも、環境変数"GEMNI_API_KEY"の値を勝手に参照するが、可読性のため代入
        client = genai.Client()

        max_retries = 3
        for i in range(max_retries):
            # generate_contentメソッドは内部的にHTTPレスポンスコード200以外の場合は例外を発生させる
            try:
                response = await client.aio.models.generate_content(  # リクエスト
                    model=self.model,
                    contents=self.prompt + "\n" + self.data,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        response_mime_type="application/json",  # 構造化出力
                        response_json_schema=TrailConditionSchemaList.model_json_schema(),
                        thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),
                    ),
                )
                print("Geminiによる要約を受け取りました。")
                break
            except ServerError:
                await super().handle_server_error(i, max_retries)
            except ClientError as e:
                super().handle_client_error(e)
            except Exception as e:
                super().handle_unexpected_error(e)

        data = super().check_response(response.text)

        stats = TokenStats(
            response.usage_metadata.prompt_token_count,
            response.usage_metadata.thoughts_token_count,
            response.usage_metadata.candidates_token_count,
            len(self.prompt),
            len(response.text),
            self.model,
        )

        return data, stats


# テスト用コードは削除されました
# テスト実行は以下のコマンドを使用してください:
# docker compose exec web uv run manage.py test_llm
#
# 使用例:
# config = LlmConfig.from_site("okutama", data=scraped_data, model="deepseek-reasoner")
# client = DeepseekClient(config)  # api_keyは自動取得
# data, stats = await client.generate()
