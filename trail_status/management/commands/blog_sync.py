import asyncio
import logging
from typing import Any

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from httpx import AsyncClient

from trail_status.models import BlogFeed, DataSource
from trail_status.services.blog_fetcher import BlogFeedSchema, BlogFetcher

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "巡視ブログの自動スクレイピング・DB同期パイプライン"

    def handle(self, *args, **options):
        logger.info("blog_syncコマンド開始")

        sources = DataSource.objects.filter(data_format="BLOG")
        self.stdout.write(f"全てのWEB情報源を処理: {len(sources)}件")

        # メイン処理
        results: list[list[BlogFeedSchema] | BaseException] = asyncio.run(self.get_all_feeds(sources))

        now = timezone.now()
        for source, result in zip(sources, results):
            if isinstance(result, BaseException):
                logger.error(f"情報源{source.id}の処理でエラー発生。詳細: {result}")
                continue
            
            existing_data:BlogFeed = BlogFeed.objects.filter(source__id=source.id)
            
            # フィードのURLで既存データと照合
            existing_urls = set(existing_data.values_list("url", flat=True))
            obtained_urls = {feed.url for feed in result}
            new_urls = obtained_urls - existing_urls

            # レコード新規作成処理
            new_records= []
            for feed in result:
                if feed.url in new_urls:    
                    new_records.append(BlogFeed(
                        source=source,
                        created_at=now,
                        **feed.model_dump()
                    ))

            if new_urls:    
                logger.info(f"新規作成予定: {source.name} - {len(new_urls)}件")
            else:
                logger.info(f"{source.name}: ブログ更新なし")
        
        with transaction.atomic():
            BlogFeed.objects.bulk_create(new_records)
        
        logger.info(f"{len(new_records)}件のブログを新規取得")
        self.stdout.write(
            self.style.SUCCESS(f"✅ {len(new_records)}件のブログを新規取得")
        )


    async def get_all_feeds(self, source_list: list[DataSource]) -> list[list[BlogFeedSchema] | BaseException]:
        """各情報源のフィードデータをすべて取得しリストで返却"""
        url_list = [source.url1 for source in source_list]
        async with AsyncClient() as client:
            tasks = [BlogFetcher(url)(client) for url in url_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

