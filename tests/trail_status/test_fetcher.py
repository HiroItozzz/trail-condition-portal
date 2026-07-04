from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from trail_status.services.fetcher import DataFetcher


class SetUp:
    def setup_method(self):
        self.url = "https://example.com/trail"
        self.fetcher = DataFetcher(self.url)
        self.fetcher.headers = {"User-Agent": "dummy"}


class TestFetcher(SetUp):
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "side_effect,expected,call_count",
        [
            (
                httpx.HTTPStatusError("ネットワークエラー", request=MagicMock(), response=MagicMock()),
                httpx.HTTPStatusError,
                3,
            ),
            (Exception, Exception, 1),
        ],
    )
    async def test_fetch_html_exception_raised(self, side_effect, expected, call_count):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=side_effect)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.raises(expected):
            await self.fetcher.fetch_html(mock_client)

        mock_client.get.assert_called_with(self.url, headers=self.fetcher.headers)
        assert mock_client.get.call_count == call_count

    @pytest.mark.asyncio
    async def test_parse_html(self):
        """テキストパースの結合テスト"""

        # HTTPレスポンスをモック
        mock_response_text = """
        <html>
            <body>
                <h1>登山道情報</h1>
                <p>通行止めの情報があります。</p>
            </body>
        </html>
        """
        text = self.fetcher.fetch_parsed_text(mock_response_text)

        assert len(text) > 0
        assert all(w in text for w in ["登山道情報", "通行止め"])

    @pytest.mark.asyncio
    async def test_parse_html_failure(self, monkeypatch):
        """テキスト抽出失敗時のフォールバックの単体テスト"""

        # 抽出失敗（空文字返却）
        monkeypatch.setattr(DataFetcher, "_extract_content", mock_content := MagicMock(return_value=""))

        dummy_response_text = """
        <html>
            <body>
                <h1>登山道情報</h1>
                <p>通行止めの情報があります。</p>
            </body>
        </html>
        """

        text = self.fetcher.fetch_parsed_text(dummy_response_text)

        assert all(w in text for w in ["登山道情報", "通行止め"])
        mock_content.assert_called_once_with(dummy_response_text, include_links=True)

    @pytest.mark.asyncio
    async def test_content_hash_calculation(self):
        """コンテンツハッシュ計算の結合テスト"""
        html = "<html><body><p>テスト</p></body></html>"

        hash1 = self.fetcher.calculate_content_hash(html)
        hash2 = self.fetcher.calculate_content_hash(html)

        # 同じ内容なら同じハッシュ
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256は64文字

    @pytest.mark.asyncio
    async def test_content_change_detection(self):
        """コンテンツ変更検知のテスト"""
        html1 = "<html><body><p>テスト1</p></body></html>"
        html2 = "<html><body><p>テスト2</p></body></html>"

        # 初回（previous_hash=None）
        has_changed, hash1 = self.fetcher.has_content_changed(html1, None)
        assert has_changed is True

        # 同じ内容
        has_changed, hash2 = self.fetcher.has_content_changed(html1, hash1)
        assert has_changed is False

        # 内容が変更
        has_changed, hash3 = self.fetcher.has_content_changed(html2, hash1)
        assert has_changed is True
        assert hash3 != hash1
