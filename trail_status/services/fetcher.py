import hashlib
import logging
from typing import Optional

import httpx
import trafilatura
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, url: str):
        self.url = url
        self.headers = {
            "User-Agent": "trail-condition-portal/1.0 (trail-info.jp; +https://github.com/HiroItozzz/trail-condition-portal)"
        }

    @retry(
        stop=stop_after_attempt(3),  # 3回リトライ
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数バックオフ（2s, 4s, 8s...）
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError)),
        reraise=True,  # 3回失敗したら最後のエラーを投げる
    )
    async def fetch_html(self, client: httpx.AsyncClient) -> str:
        """生HTMLのスクレイピング"""
        try:
            response = await client.get(self.url, headers=self.headers)
            response.raise_for_status()
            return response.text

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} for {self.url}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error fetching {self.url}")
            raise

    async def fetch_parsed_text(self, response_text: str) -> str:
        """
        単一のURLからテキストを取得。リトライとロギング付き。
        """
        logger.debug(f"コンテンツ抽出開始: {self.url}")

        # HTMLボディから本文のみを抽出（メニューやフッターを自動で削る）
        # include_links=True: AIがreference_URLを抽出できるように
        content = self._extract_content(response_text, include_links=True)

        if not content:
            logger.warning(f"Trafilaturaがコンテンツの抽出に失敗しました。生のテキストを出力します。URL: {self.url}")
            content = trafilatura.html2txt(response_text)

        logger.debug(f"コンテンツ抽出終了: {self.url} (抽出文字数: {len(content)})")
        return content

    def calculate_content_hash(self, html: str) -> str:
        """
        HTMLからtrafilaturaで抽出した内容のハッシュ値を計算

        Args:
            html: HTML文字列

        Returns:
            str: SHA256ハッシュ値（64文字）

        Notes:
            - include_links=False: URL変更だけでハッシュが変わるのを防ぐ
            - より安定したハッシュ値を得るため、純粋なテキストのみを使用
        """
        # include_links=False: リンクURL変更を無視（本文の変更のみ検知）
        normalized_content = self._extract_content(html, include_links=False, include_comments=False)

        # UTF-8エンコードしてハッシュ計算
        return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

    def has_content_changed(self, html: str, previous_hash: Optional[str]) -> tuple[bool, str]:
        """
        コンテンツが変更されているかをハッシュで判定

        Args:
            html: 現在のHTML
            previous_hash: 前回のハッシュ値（None の場合は初回）

        Returns:
            tuple[bool, str]: (変更フラグ, 新しいハッシュ値)
        """
        current_hash = self.calculate_content_hash(html)

        # 初回スクレイピングまたはハッシュが異なる場合は変更あり
        has_changed = previous_hash is None or current_hash != previous_hash

        if previous_hash is None:
            logger.debug(f"初回スクレイピング - ハッシュ: {current_hash[:8]}...")
        elif has_changed:
            logger.debug(f"コンテンツ変更検知 - 旧: {previous_hash[:8]}... 新: {current_hash[:8]}...")
        else:
            logger.debug(f"コンテンツ変更なし - ハッシュ: {current_hash[:8]}...")

        return has_changed, current_hash

    def _extract_content(self, html: str, include_links: bool = False, include_comments: bool = False) -> str:
        """
        TrafilaturaでHTMLからコンテンツを抽出（共通処理）

        Args:
            html: HTML文字列
            include_links: リンク情報を含めるか（AI用テキスト: True, ハッシュ計算: False）
            include_comments: コメントを含めるか（デフォルト: False）

        Returns:
            str: 抽出されたテキスト（空の場合は空文字列）

        Notes:
            - include_links=True: リンクテキストとURLを含める（AI用、reference_URL抽出のため）
            - include_links=False: 純粋なテキストのみ（ハッシュ計算用、URL変更を無視）
        """
        content = trafilatura.extract(
            html,
            include_tables=True,  # 登山情報の核心（表）を維持
            include_links=include_links,
            include_comments=include_comments,
        )
        return content or ""
