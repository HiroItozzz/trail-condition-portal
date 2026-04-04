import asyncio
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from httpx import AsyncClient

from trail_status.models import BlogFeed, DataSource
from trail_status.services.blog_fetcher import BlogFeedSchema, BlogFetcher

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "巡視ブログの自動スクレイピング・DB同期パイプライン"

    def handle(self, *args, **options):
        logger.info("blog_syncコマンド開始")

        sources = DataSource.objects.filter(data_format="BLOG")
        all_exisiting_feeds = BlogFeed.objects.filter(source__in=sources)
        self.stdout.write(f"全てのWEB情報源を処理: {len(sources)}件")

        # メイン処理
        results: list[list[BlogFeedSchema] | BaseException] = asyncio.run(self.get_all_feeds(sources))

        now = timezone.now()
        new_records = []
        for source, result in zip(sources, results):
            if isinstance(result, BaseException):
                logger.error(f"情報源{source.id}の処理でエラー発生。詳細: {result}")
                continue

            # 各記事のURLで照合
            existing_feed_urls = set(all_exisiting_feeds.filter(source__id=source.id).values_list("url", flat=True))
            obtained_urls = {feed.url for feed in result}
            new_urls = obtained_urls - existing_feed_urls

            # 新規情報源の判定
            is_first_sync = not existing_feed_urls

            # レコード新規作成処理
            for feed in result:
                if feed.url in new_urls:
                    new_records.append(
                        BlogFeed(
                            source=source,
                            created_at=now,
                            disabled=is_first_sync,  # 初回登録は管理画面で人間が情報の有効化を行う
                            **feed.model_dump(),
                        )
                    )

            if new_urls:
                logger.info(f"新規作成予定: {source.name} - {len(new_urls)}件")
            else:
                logger.info(f"{source.name}: ブログ更新なし")

        BlogFeed.objects.bulk_create(new_records)

        logger.info(f"{len(new_records)}件のブログを新規取得")
        self.stdout.write(self.style.SUCCESS(f"✅ {len(new_records)}件のブログを新規取得"))

    async def get_all_feeds(self, source_list: list[DataSource]) -> list[list[BlogFeedSchema] | BaseException]:
        """各情報源のフィードデータをすべて取得しリストで返却"""
        url_list = [source.url1 for source in source_list]
        async with AsyncClient() as client:
            tasks = [BlogFetcher(url)(client) for url in url_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
