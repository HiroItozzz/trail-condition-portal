import asyncio
import html
import logging
import re
from datetime import datetime
from datetime import timezone as dt_timezone
from pathlib import Path

import feedparser
from feedparser import FeedParserDict
from httpx import AsyncClient, HTTPStatusError
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class BlogFeedSchema(BaseModel):
    title: str = Field(description="記事のタイトル", max_length=100)
    summary: str = Field(description="記事の冒頭", max_length=200)
    url: str = Field(description="記事へのリンクURL", max_length=500)
    published_at: datetime = Field(description="投稿日時")

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, values: dict) -> dict:
        for key in ("title", "summary"):
            v = values.get(key, "")
            v = html.unescape(v)
            v = re.sub(r"<.*?>", "", v)
            v = v.replace("\n", " ").replace("\\n", " ").replace("\u3000", " ")
            values[key] = v
        values["title"] = values["title"][:100]
        values["summary"] = values["summary"][:200]
        return values


class BlogFetcher:
    headers = {
        "User-Agent": "trail-condition-portal/1.0 (trail-info.jp; +https://github.com/HiroItozzz/trail-condition-portal)"
    }

    def __init__(self, url: str, id: int | None = None, name: str | None = None):
        self.url = url
        self.id = id
        self.name = name

    async def __call__(self, client: AsyncClient) -> list[BlogFeedSchema]:
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
    def parse_feed(xml: str) -> list[BlogFeedSchema]:
        data: FeedParserDict = feedparser.parse(xml)
        feed_list = []
        for entry in data.entries:
            feed_list.append(
                BlogFeedSchema(
                    title=entry.title,
                    summary=entry.summary,
                    published_at=datetime(*entry.published_parsed[:6], tzinfo=dt_timezone.utc),
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
