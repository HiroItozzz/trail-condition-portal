import asyncio
from typing import Any

import httpx

from .fetcher import DataFetcher
from .llm_client import DeepseekClient, GeminiClient, LlmConfig
from .llm_stats import LlmStats, TokenStats
from .schema import TrailConditionSchemaList
from .types import SourceDataSingle, UpdatedDataList, UpdatedDataSingle


class TrailConditionPipeline:
    """登山道状況の自動処理パイプライン（純粋async処理）"""

    def __init__(self):
        pass

    async def process_source_data(self, source_data_list: list[SourceDataSingle], model: str) -> UpdatedDataList:
        """ソースデータリストを並行処理（Django ORM一切なし）"""
        async with httpx.AsyncClient() as client:
            tasks = []
            for source_data in source_data_list:
                # コア処理
                task = self.process_single_source_data(client, source_data, model)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return list(zip(source_data_list, results))

    # コア処理
    async def process_single_source_data(
        self, client: httpx.AsyncClient, source_data: SourceDataSingle, model: str
    ) -> UpdatedDataSingle:
        """単一ソースデータの処理パイプライン（純粋async）"""
        try:
            # 1. スクレイピング
            scraped_text = await self._fetch_content(client, source_data["url1"])
            if not scraped_text.strip():
                return {"error": "スクレイピング結果が空でした"}

            # 2. AI解析
            ai_result, stats = await self._analyze_with_ai(source_data, scraped_text, model)

            return {
                "success": True,
                "scraped_length": len(scraped_text),
                "extracted_trail_conditions": ai_result,  # TrailConditionSchemaListのまま
                "stats": stats,  # LlmStatsオブジェクト
            }

        except Exception as e:
            return {"error": str(e)}

    async def _fetch_content(self, client: httpx.AsyncClient, url: str):
        """コンテンツのスクレイピング"""
        fetcher = DataFetcher()
        return await fetcher.fetch_text(client, url)

    async def _analyze_with_ai(
        self, source_data: SourceDataSingle, scraped_text: str, model: str
    ) -> tuple[TrailConditionSchemaList, LlmStats]:
        """AI解析処理"""
        import time

        prompt_filename = self._get_prompt_filename_from_data(source_data)

        try:
            site_prompt = LlmConfig.load_prompt(prompt_filename)
            config = LlmConfig(site_prompt=site_prompt, data=scraped_text, model=model)
        except FileNotFoundError:
            raise ValueError(f"プロンプトファイルが見つかりません: {prompt_filename}")

        # AIクライアントの選択
        if model.startswith("deepseek"):
            ai_client = DeepseekClient(config)
        elif model.startswith("gemini"):
            ai_client = GeminiClient(config)
        else:
            raise ValueError(f"サポートされていないモデル: {model}")

        # 実行時間測定
        start_time = time.time()
        ai_result, token_stats = await ai_client.generate()
        execution_time = time.time() - start_time

        # LlmStatsでラップして実行時間を追加
        llm_stats = LlmStats(token_stats)
        llm_stats.execution_time = execution_time

        return ai_result, llm_stats

    # AIモジュールからの出力をpydanticクラスに変更後、削除予定
    def _convert_to_conditions_list(self, ai_result: list[dict]) -> list[dict]:
        """AIの出力を条件リストに変換"""
        ai_schema_list = TrailConditionSchemaList.model_validate(ai_result)
        return [item.model_dump() for item in ai_schema_list.trail_condition_records]

    def _get_prompt_filename_from_data(self, source_data: SourceDataSingle) -> str:
        """ソースデータからプロンプトファイル名を取得"""
        # 形式: {id:03d}_{prompt_key}.yaml
        source_id = source_data["id"]
        prompt_key = source_data["prompt_key"]
        return f"{source_id:03d}_{prompt_key}.yaml"
