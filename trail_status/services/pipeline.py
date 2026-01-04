import asyncio
import logging

import httpx

from .fetcher import DataFetcher
from .llm_client import DeepseekClient, GeminiClient, LlmConfig
from .llm_stats import LlmStats
from .schema import TrailConditionSchemaList
from .types import ModelDataSingle, UpdatedDataList, UpdatedDataSingle

logger = logging.getLogger(__name__)


class TrailConditionPipeline:
    """登山道状況の自動処理パイプライン（純粋async処理）"""

    def __init__(self):
        pass

    async def process_source_data(self, source_data_list: list[ModelDataSingle], ai_model: str) -> UpdatedDataList:
        """ソースデータリストを並行処理（Django ORM一切なし）"""
        logger.info(f"パイプライン処理開始 - 対象: {len(source_data_list)}件, モデル: {ai_model or 'デフォルト'}")

        async with httpx.AsyncClient() as client:
            tasks = []
            for source_data in source_data_list:
                # コア処理
                task = self.process_single_source_data(client, source_data, ai_model)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"パイプライン処理完了 - 処理件数: {len(results)}")
        return list(zip(source_data_list, results))

    # コア処理
    async def process_single_source_data(
        self, client: httpx.AsyncClient, source_data: ModelDataSingle, ai_model: str
    ) -> UpdatedDataSingle:
        """単一ソースデータの処理パイプライン（純粋async）"""
        logger.debug(f"処理開始: {source_data['name']} (ID: {source_data['id']})")

        try:
            # 1. スクレイピング
            scraped_html = await self._fetch_raw_content(client, source_data["url1"])
            if not scraped_html.strip():
                logger.warning(f"スクレイピング結果が空: {source_data['name']}")
                return {"error": "スクレイピング結果が空でした"}

            # 2. ハッシュベース変更検知
            fetcher = DataFetcher()
            content_changed, new_hash = fetcher.has_content_changed(scraped_html, source_data.get("content_hash"))
            
            if not content_changed:
                logger.info(f"コンテンツ変更なし（ソースID: {source_data['id']}）- LLM処理をスキップ")
                return {
                    "success": True, 
                    "content_changed": False, 
                    "new_hash": new_hash,
                    "scraped_length": len(scraped_html),
                }

            # 3. trafilaturaでテキスト抽出
            scraped_text = await self._extract_text_content(client, source_data["url1"])
            if not scraped_text.strip():
                logger.warning(f"テキスト抽出結果が空: {source_data['name']}")
                return {"error": "テキスト抽出結果が空でした"}

            # 4. AI解析（コンテンツ変更時のみ）
            logger.info(f"AI解析開始: {source_data['name']} - モデル: {ai_model or 'デフォルト'}")
            config, ai_result, stats = await self._analyze_with_ai(source_data, scraped_text, ai_model)
            logger.info(f"AI解析完了: {source_data['name']} - コスト: ${stats.total_fee:.4f}, 実行時間: {stats.execution_time:.2f}秒")

            return {
                "success": True,
                "content_changed": True,
                "new_hash": new_hash,
                "scraped_length": len(scraped_html),
                "extracted_trail_conditions": ai_result,  # TrailConditionSchemaListのまま
                "stats": stats,  # LlmStatsオブジェクト
                "config": config,  # LlmConfigオブジェクト
            }

        except Exception as e:
            logger.error(f"処理エラー: {source_data['name']} - {str(e)}")
            return {"error": str(e)}

    async def _fetch_raw_content(self, client: httpx.AsyncClient, url: str) -> str:
        """生HTMLのスクレイピング（ハッシュ計算用）"""
        fetcher = DataFetcher()
        try:
            response = await client.get(url, headers=fetcher.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"HTMLスクレイピング失敗 - URL: {url}, エラー: {e}")
            raise

    async def _extract_text_content(self, client: httpx.AsyncClient, url: str) -> str:
        """テキスト抽出（AI解析用）- DataFetcherのリトライロジック活用"""
        fetcher = DataFetcher()
        return await fetcher.fetch_text(client, url)

    async def _analyze_with_ai(
        self, source_data: ModelDataSingle, scraped_text: str, ai_model: str | None
    ) -> tuple[LlmConfig, TrailConditionSchemaList, LlmStats]:
        """AI解析処理"""
        import time

        prompt_filename = self._get_prompt_filename_from_data(source_data)

        try:
            config = LlmConfig.from_file(prompt_filename, data=scraped_text, model=ai_model)
        except FileNotFoundError:
            logger.error(f"プロンプトファイルが見つかりません: {prompt_filename}")
            raise ValueError(f"プロンプトファイルが見つかりません: {prompt_filename}")

        # AIクライアントの選択
        if config.model.startswith("deepseek"):
            ai_client = DeepseekClient(config)
        elif config.model.startswith("gemini"):
            ai_client = GeminiClient(config)
        else:
            raise ValueError(f"サポートされていないモデル: {ai_model}")

        # 実行時間測定
        start_time = time.time()
        ai_result, token_stats = await ai_client.generate()
        execution_time = time.time() - start_time

        # LlmStatsでラップして実行時間を追加
        llm_stats = LlmStats(token_stats)
        llm_stats.execution_time = execution_time

        return config, ai_result, llm_stats

    def _get_prompt_filename_from_data(self, source_data: ModelDataSingle) -> str:
        """ソースデータからプロンプトファイル名を取得"""
        # 形式: {id:03d}_{prompt_key}.yaml
        source_id = source_data["id"]
        prompt_key = source_data["prompt_key"]
        return f"{source_id:03d}_{prompt_key}.yaml"
