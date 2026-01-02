import asyncio
from typing import Any

import httpx

from .fetcher import DataFetcher
from .llm_client import DeepseekClient, GeminiClient, LlmConfig
from .llm_stats import TokenStats
from .schema import TrailConditionSchemaList
from .types import SourceDataSingle, UpdatedDataList, UpdatedDataSingle


class TrailConditionPipeline:
    """登山道状況の自動処理パイプライン（純粋async処理）"""

    def __init__(self):
        self.site_name_mapping = {
            "奥多摩": "okutama_vc",
            "okutama": "okutama_vc",
            "御岳": "mitake",
            "mitake": "mitake",
            # 必要に応じて追加
        }

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

            # 3. スキーマ変換（DBに依存しない）
            ai_conditions = self._convert_to_conditions_list(ai_result)

            return {
                "success": True,
                "scraped_length": len(scraped_text),
                "ai_conditions": ai_conditions,
                "stats": stats.to_dict(),
            }

        except Exception as e:
            return {"error": str(e)}

    async def _fetch_content(self, client: httpx.AsyncClient, url: str):
        """コンテンツのスクレイピング"""
        fetcher = DataFetcher()
        return await fetcher.fetch_text(client, url)

    async def _analyze_with_ai(
        self, source_data: SourceDataSingle, scraped_text: str, model: str
    ) -> tuple[list[dict], TokenStats]:
        """AI解析処理"""
        site_name = self._guess_site_name_from_data(source_data)

        try:
            config = LlmConfig.from_site(site_name, data=scraped_text, model=model)
        except FileNotFoundError:
            raise ValueError(f"サイト設定ファイルが見つかりません: {site_name}")

        # AIクライアントの選択
        if model.startswith("deepseek"):
            ai_client = DeepseekClient(config)
        elif model.startswith("gemini"):
            ai_client = GeminiClient(config)
        else:
            raise ValueError(f"サポートされていないモデル: {model}")

        return await ai_client.generate()

    def _convert_to_conditions_list(self, ai_result: list[dict]) -> list[dict]:
        """AIの出力を条件リストに変換"""
        ai_schema_list = TrailConditionSchemaList.model_validate(ai_result)
        return [item.model_dump() for item in ai_schema_list.trail_condition_records]

    ### DBに格納されたレコードから取得に変更予定
    def _guess_site_name_from_data(self, source_data: SourceDataSingle) -> str:
        """ソースデータからサイト名を推測"""
        name_lower = source_data["name"].lower()

        for keyword, site_name in self.site_name_mapping.items():
            if keyword in name_lower:
                return site_name

        # デフォルト
        return "okutama_vc"

    # ユーティリティ関数
    def add_site_mapping(self, keyword, site_name):
        """サイト名マッピングを追加"""
        self.site_name_mapping[keyword] = site_name
