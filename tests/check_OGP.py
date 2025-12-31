import requests
from bs4 import BeautifulSoup


def get_preview(url):
    """どちらのサイトでもOGPを試す → なければ自分で抽出"""
    try:
        # OGPを探す
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")

        og_data = {}

        # OGPタグを取得
        og_title = soup.find("meta", property="og:title")
        og_description = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        if og_title:  # OGPあり！
            og_data = {
                "title": og_title.get("content", ""),
                "description": og_description.get("content", "") if og_description else "",
                "image": og_image.get("content", "") if og_image else "",
                "has_ogp": True,
            }
        else:  # OGPなし → 自分で抽出
            title = soup.title.string if soup.title else ""
            # 本文から適当に抜き出す（サイトごとに調整が必要）
            og_data = {
                "title": title,
                "description": title[:100] + "...",  # 仮
                "image": "",
                "has_ogp": False,
            }

        return og_data

    except Exception as e:
        return {"error": str(e), "has_ogp": False}


# YAMAPの適当な記事でテスト
if __name__ == "__main__":
    URL = "https://www.yamareco.com/modules/yamareco/detail-9068927.html"
    print("OGP Test:")
    print(get_preview(URL))
