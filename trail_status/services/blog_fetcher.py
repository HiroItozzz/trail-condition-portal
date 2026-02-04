import asyncio
import logging
from datetime import datetime
from pathlib import Path

import feedparser
from httpx import AsyncClient, HTTPStatusError
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BlogFeed(BaseModel):
    title: str
    summary: str
    published_at: datetime
    url: str


class BlogFetcher:
    headers = {
        "User-Agent": "trail-condition-portal/1.0 (trail-info.jp; +https://github.com/HiroItozzz/trail-condition-portal)"
    }

    def __init__(self, url: str, id: int | None = None, name: str | None = None):
        self.url = url
        self.id = id
        self.name = name

    async def __call__(self, client: AsyncClient) -> list[BlogFeed]:
        xml = await self.fetch_url(client)
        return self.parse_feed(xml)

    async def fetch_url(self, client: AsyncClient) -> str:
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

    @staticmethod
    def parse_feed(xml: str) -> list[BlogFeed]:
        data = feedparser.parse(xml)
        feed_list = []
        for entry in data.entries:
            feed_list.append(
                BlogFeed(
                    title=entry.title,
                    summary=entry.summary[:100],
                    published_at=datetime(*entry.published_parsed[:6]),
                    url=entry.link,
                )
            )
        return feed_list


# -----------------------------------------------------------------------------
async def main():
    url_list = [url.strip() for url in blog_urls.split("\n") if url]
    async with AsyncClient() as client:
        tasks = [BlogFetcher(url)(client, property_key) for url in url_list]
        results = await asyncio.gather(*tasks)
    return results


if __name__ == "__main__":
    blog_urls = """https://okutama-sr.jpn.org/blog/feed/
    https://hadanovc.blogspot.com/feeds/posts/default?alt=rss
    https://nishitanzawashizenkyoushitsu.blogspot.com/feeds/posts/default
    https://www.hinohara-mori.jp/feed
    """

    property_key = "summary"
    results = asyncio.run(main())
    output_text = ""
    output_path = Path.cwd() / f"feed_{property_key}_sample.txt"
    for result in results:
        for entry in result:
            output_text += ". ".join(map(str, entry)) + "\n"
            print(entry)
    output_path.write_text(output_text, encoding="utf-8")
