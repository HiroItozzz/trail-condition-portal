"""
DataFetcherのテスト
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx

from trail_status.services.fetcher import DataFetcher


@pytest.mark.asyncio
async def test_fetch_text_success():
    """テキスト取得成功のテスト（モック使用）"""
    fetcher = DataFetcher()

    # HTTPレスポンスをモック
    mock_response = MagicMock()
    mock_response.text = """
    <html>
        <body>
            <h1>登山道情報</h1>
            <p>通行止めの情報があります。</p>
        </body>
    </html>
    """

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    text = await fetcher.fetch_text(mock_client, "https://example.com/trail")

    assert len(text) > 0
    assert "登山道情報" in text or "通行止め" in text  # trafilaturaで抽出されたテキスト


@pytest.mark.asyncio
async def test_content_hash_calculation():
    """コンテンツハッシュ計算のテスト"""
    fetcher = DataFetcher()
    html = "<html><body><p>テスト</p></body></html>"

    hash1 = fetcher.calculate_content_hash(html)
    hash2 = fetcher.calculate_content_hash(html)

    # 同じ内容なら同じハッシュ
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256は64文字


@pytest.mark.asyncio
async def test_content_change_detection():
    """コンテンツ変更検知のテスト"""
    fetcher = DataFetcher()
    html1 = "<html><body><p>テスト1</p></body></html>"
    html2 = "<html><body><p>テスト2</p></body></html>"

    # 初回（previous_hash=None）
    has_changed, hash1 = fetcher.has_content_changed(html1, None)
    assert has_changed is True

    # 同じ内容
    has_changed, hash2 = fetcher.has_content_changed(html1, hash1)
    assert has_changed is False

    # 内容が変更
    has_changed, hash3 = fetcher.has_content_changed(html2, hash1)
    assert has_changed is True
    assert hash3 != hash1
