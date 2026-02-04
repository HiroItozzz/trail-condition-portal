import asyncio
import logging
from typing import Any

from django.core.management.base import BaseCommand
from httpx import AsyncClient

from trail_status.models.source import DataSource
from trail_status.services.blog_fetcher import BlogFeed, BlogFetcher
from trail_status.services.types import PatrolBlogDict

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "巡視ブログの自動スクレイピング・DB同期パイプライン"

    def handle(self, *args, **options):
        logger.info("blog_syncコマンド開始")

        sources = DataSource.objects.filter(data_format="BLOG")
        source_data_list: list[PatrolBlogDict] = [
            {"id": source.id, "name": source.name, "url": source.url1} for source in sources
        ]
        self.stdout.write(f"全てのWEB情報源を処理: {len(source_data_list)}件")

        # メイン処理
        results: list[BlogFeed | BaseException] = asyncio.run(self.get_all_feed(source_data_list))

        for source_data, result in zip(source_data_list, results):
            if hasattr(result, BaseException):
                logger.error(f"情報源{source_data["id"]}の処理でエラー発生。詳細: {result}")
                continue
            
            取得したブログフィードをブログフィードモデルで永続化するコード
            更新有無の判定:　既存ブログフィード集合-取得した集合の差集合
            取得したsummaryの正規化1: re.sub(re.compile('<.*?>'), '', str3)
            取得したsummaryの正規化2:
            data = parsed.replace("\\n","").replace("\n","").replace("\u3000","")



    async def get_all_feed(self, source_data_list: list[PatrolBlogDict]) -> list[BlogFeed | BaseException]:
        """各情報源のフィードデータをすべて取得しリストで返却"""
        url_list = [single_data["url"] for single_data in source_data_list]
        async with AsyncClient() as client:
            tasks = [BlogFetcher(url)(client) for url in url_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

