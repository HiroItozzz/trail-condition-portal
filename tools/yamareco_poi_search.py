"""
ヤマレコ地名データ検索API テストツール

使用例:
    python tools/yamareco_poi_search.py
"""

import requests


def search_poi(name: str, area_id: int, type_id: int = 0) -> list[dict]:
    """
    ヤマレコの地名データを検索する

    Args:
        name: 検索したい地名（2文字以上で部分一致）
        area_id: エリアID（0で全エリア）
        type_id: データ種別（0で全種別、1=山頂、2=峠、3=分岐、4=登山口、6=山小屋、10=危険個所）

    Returns:
        検索結果のリスト
    """
    data = {
        "name": name,
        "area_id": area_id,
        "page": 1,
        "type_id": type_id,
    }
    r = requests.post("https://api.yamareco.com/api/v1/searchPoi", data=data)
    result = r.json()
    if result.get("err") == 0 and "poilist" in result:
        return result["poilist"]
    return []


def search_and_print(name: str, area_id: int) -> None:
    """検索して結果を表示"""
    results = search_poi(name, area_id)
    if results:
        print(f"✓ {name} (area_id={area_id}): {len(results)}件")
        for poi in results[:3]:
            print(f"    - {poi['name']} ({poi.get('elevation', '?')}m) [{poi.get('lat')}, {poi.get('lon')}]")
            print(" | ".join([f"{key}: {value}" for key, value in poi.items()]))
            
    else:
        print(f"✗ {name} (area_id={area_id}): 見つからず")


# エリアIDマッピング（AreaName → ヤマレコ area_id）
YAMARECO_AREA_MAP = {
    "OKUTAMA": 306,
    "TANZAWA": 307,
    "TAKAO": 306,
    "HAKONE": 309,
    "OKUMUSASHI": 305,
    "OKUCHICHIBU": 310,
    "DAIBOSATSU": 310,
    "SAGAMIKO": 306,
}


if __name__ == "__main__":
    # テストケース
    test_cases = [
        ("雲取山", 306),
        ("丹沢山", 307),
        ("網代城山", 306),
        ("刈寄山", 306),
        ("戸倉城山", 306),
        ("金比羅山", 306),
        ("八王子城山", 306),
        ("麻生山", 306),
        ("三室山", 306),
        ("雨山", 307),
        ("檜洞丸", 307),
        ("大岳山", 306),
    ]

    print("=== ヤマレコ地名データ検索テスト ===\n")
    for name, area_id in test_cases:
        search_and_print(name, area_id)
        print()
