import logging

import httpx
import trafilatura
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."}

    @retry(
        stop=stop_after_attempt(3),  # 3回リトライ
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数バックオフ（2s, 4s, 8s...）
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError)),
        reraise=True,  # 3回失敗したら最後のエラーを投げる
    )
    async def fetch_text(self, client: httpx.AsyncClient, url: str) -> str:
        """
        単一のURLからテキストを取得。リトライとロギング付き。
        """

        try:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()

            # HTMLから本文のみを抽出（メニューやフッターを自動で削る）
            content = trafilatura.extract(
                response.text,
                include_tables=True,  # 登山情報の核心（表）を維持
                include_links=True,  # 詳細PDFへのリンクなどを維持
            )
            if content is None:
                logger.warning(f"Trafilaturaがコンテンツの抽出に失敗しました。生のテキストを出力します。URL: {url}")
                content = trafilatura.html2txt(response.text)

            return content or ""

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} for {url}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error fetching {url}")
            raise
