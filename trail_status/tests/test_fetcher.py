import pytest
import httpx
from trail_status.services.fetcher import DataFetcher

@pytest.mark.asyncio
async def test_okutama_fetch_real():
    target_url = "https://mitakevc.ces-net.jp/trailinformation.html"
    fetcher = DataFetcher()
    
    async with httpx.AsyncClient() as client:
        text = await fetcher.fetch_text(client, target_url)
        print(text)
        assert len(text) > 0
        assert "通行止" in text  # 期待するキーワードが含まれているか