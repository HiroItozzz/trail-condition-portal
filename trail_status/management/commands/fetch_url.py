import asyncio
import logging
import pathlib
import shutil
import sys

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Max

from trail_status.models import DataSource
from trail_status.services.fetcher import DataFetcher

logger = logging.getLogger(__name__)

OUTPUT_DIR: pathlib.Path = settings.BASE_DIR / "outputs/fetched_content/"


class Command(BaseCommand):
    help = "Trafilaturaで対象ソースIDの内容を取得する"

    def add_arguments(self, parser):
        parser.add_argument("source_id", type=int, help="情報源ID")

    def handle(self, *args, **options):
        pk = options.get("source_id")

        try:
            data_source = DataSource.objects.get(pk=pk)
        except DataSource.DoesNotExist:
            print(f"情報源ID {pk} は存在しません", file=sys.stderr)
            print(f"情報源IDの最大値: {DataSource.objects.aggregate(Max('pk'))['pk__max']}")
            sys.exit(1)

        url = data_source.url1
        text = asyncio.run(self.fetch_url(url))

        width, _ = shutil.get_terminal_size()
        print(f"情報源: {data_source.name}".center(width - 3, "─"))
        print(text)

        OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
        output_path = OUTPUT_DIR / f"{data_source.pk:03}_{data_source.prompt_key}.txt"
        output_path.write_text(text, encoding="utf-8")
        print(f"取得したテキストを{output_path}に保存しました")


    async def fetch_url(self, url):
        async with httpx.AsyncClient() as client:
            fetcher = DataFetcher(url)
            html = await fetcher.fetch_html(client)

            parsed_text = fetcher.fetch_parsed_text(html)
            if not parsed_text.strip():
                logger.warning("テキスト抽出結果が空でした")
                return

            return parsed_text
