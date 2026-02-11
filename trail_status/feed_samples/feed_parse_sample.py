import asyncio
import logging
from pathlib import Path

import feedparser
from httpx import AsyncClient, HTTPStatusError

logger = logging.getLogger(__name__)

blog_urls = """https://okutama-sr.jpn.org/blog/feed/
https://hadanovc.blogspot.com/feeds/posts/default?alt=rss
https://nishitanzawashizenkyoushitsu.blogspot.com/feeds/posts/default
https://www.hinohara-mori.jp/feed
"""


class BlogFetcher:
    headers = {
        "User-Agent": "trail-condition-portal/1.0 (trail-info.jp; +https://github.com/HiroItozzz/trail-condition-portal)"
    }

    def __init__(self, url: str):
        self.url = url

    async def __call__(self, client: AsyncClient, property_key: str):
        xml = await self.fetch_url(client)
        return self.parse_feed(xml, property_key)

    async def fetch_url(self, client: AsyncClient):
        try:
            response = await client.get(self.url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} for {self.url}")
            raise e
        except Exception as e:
            logger.exception(f"Unexpected error fetching {self.url}")
            raise e

    def parse_feed(self, xml: str, property_key: str):
        data = feedparser.parse(xml)
        title_list = [(idx, getattr(entry, property_key, None)) for idx, entry in enumerate(data.entries, start=1)]
        return title_list


async def main():
    url_list = [url.strip() for url in blog_urls.split("\n") if url]
    async with AsyncClient() as client:
        tasks = [BlogFetcher(url)(client, property_key) for url in url_list]
        results = await asyncio.gather(*tasks)
    return results


if __name__ == "__main__":
    from datetime import datetime
    property_key = "tags"
    results = asyncio.run(main())
    output_text = ""
    output_path = Path.cwd() / f"feed_{property_key}_sample.txt"
    for result in results:
        for entry in result:
            output_text += ". ".join(map(str, entry)) + "\n"
            print(entry)
    output_path.write_text(output_text, encoding="utf-8")
