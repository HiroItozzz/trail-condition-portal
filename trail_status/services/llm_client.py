import os
import sys

import django

# プロジェクトのルートをパスに追加
sys.path.append("/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")  # プロジェクト名に合わせて変更
django.setup()

import asyncio
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path

import yaml
from llm_stats import TokenStats
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from trail_status.services.schema import TrailConditionSchemaList

logger = logging.getLogger(__name__)

deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
prompt_path = Path("/code/trail_status/services/ai_config/mitake.yaml")
prompt = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))["prompt"]
data_path = Path("/code/trail_status/services/sample/sample_mitake.txt")
data = data_path.read_text(encoding="utf-8")


class LlmConfig(BaseModel):
    prompt: str = Field(min_length=1, description="AIに送るプロンプト")
    model: str = Field(pattern=r"^(gemini|deepseek)-.+", default="deepseek-chat", description="使用するLLMモデル")
    temperature: float = Field(default=0.3, ge=0, le=2.0, description="生成ごとの揺らぎの幅")
    api_key: str = Field(default=deepseek_api_key, min_length=1, description="API キー")
    data: str


class ConversationalAi(ABC):
    def __init__(self, config: LlmConfig):
        self.model = config.model
        self.temperature = config.temperature
        self.custom_prompt = config.prompt
        self.data = config.data
        self.api_key = config.api_key

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
        output_path = Path(f"/code/trail_status/services/sample/{self.model}_sample.json")
        output_path.write_text(response_text, encoding="utf-8")
        try:
            validated_data = TrailConditionSchemaList.model_validate_json(response_text)
            data = validated_data.model_dump()
            logger.warning(f"{self.model}が構造化出力に成功")
        except Exception:
            logger.error(f"{self.model}が構造化出力に失敗。")

            output_path = Path.cwd() / "outputs"
            output_path.mkdir(exist_ok=True)
            file_path = output_path / "__summary.txt"
            file_path.write_text(response_text, encoding="utf-8")

            logger.error(f"{file_path}へ出力を保存しました。")
            raise

        return data


class DeepseekClient(ConversationalAi):
    @property
    def prompt(self):
        STATEMENT = f"【重要】次の行から示す要請はこのPydanticモデルに合うJSONで出力してください: {TrailConditionSchemaList.model_json_schema()}\n"
        return STATEMENT + self.custom_prompt + self.data

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
                    messages=[{"role": "user", "content": self.prompt}],
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
                    sys.exit(1)
                elif "402" in str(e):
                    logger.error("残高が不足しているようです。アカウントを確認してください。")
                    logger.error(f"実行を中止します。詳細：{e}")
                    sys.exit(1)
                elif "422" in str(e):
                    logger.error("リクエストに無効なパラメータが含まれています。設定を見直してください。")
                    logger.error(f"実行を中止します。詳細：{e}")
                    sys.exit(1)
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
            len(self.prompt),
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
                    contents=self.custom_prompt + "\n" + self.data,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        response_mime_type="application/json",  # 構造化出力
                        response_json_schema=TrailConditionSchemaList.model_json_schema(),
                        thinking_config=types.ThinkingConfig(thinking_budget=2000),
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
            len(self.custom_prompt),
            len(response.text),
            self.model,
        )

        return data, stats


if __name__ == "__main__":
    d_config = LlmConfig(model="deepseek-reasoner", prompt=prompt, data=data)
    g_config = LlmConfig(model="gemini-3-flash-preview", prompt=prompt, data=data)

    results = [asyncio.run(DeepseekClient(d_config).generate())]
    # results = [asyncio.run(GeminiClient(g_config).generate())]
        
    '''    async def compare():
            results = await asyncio.gather(
                DeepseekClient(d_config).generate(), GeminiClient(g_config).generate(), return_exceptions=True
            )

            return results

        results = asyncio.run(compare())
    '''
    from pprint import pprint

    for idx, (output, stats) in enumerate(results, 1):
        print(f"==================結果{idx}=======================")
        print()
        print("=======AIによる出力=======")
        pprint(output)
        print("=======AIによるコスト分析=======")
        pprint(stats)

    '''
    from openai import OpenAI
    client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
    print(client.models.list())
    '''