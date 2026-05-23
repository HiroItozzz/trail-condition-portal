"""
ヤマレコ地名データ検索API クライアント

ヤマレコのPOI（地名データ）検索APIのラッパー。
生レスポンス取得・Pydanticモデルへのパース・表示までを提供する。
"""

from typing import Any

import httpx
from pydantic import BaseModel, Field

# エリアID一覧
_YAMARECO_AREA_MAP = {
    "OKUTAMA": 306,
    "TANZAWA": 307,
    "TAKAO": 306,
    "HAKONE": 309,
    "OKUMUSASHI": 305,
    "OKUCHICHIBU": 310,
    "DAIBOSATSU": 310,
    "SAGAMIKO": 306,
}


class LocationInfo(BaseModel):
    class TypeInfo(BaseModel):
        type_id: int
        name: str
        detail: str

    ptid: int
    title: str = Field(validation_alias="name")
    content: str = Field(default="", validation_alias="detail")
    lat: float
    lng: float = Field(validation_alias="lon")
    elevation: float
    area_id: int | None = Field(default=None, validation_alias="area")
    page_url: str | None = Field(default=None)
    photo_url: str | None = Field(default=None)
    other_names: str | None = Field(default=None)
    name_en: str | None = Field(default=None)
    yomi: str | None = Field(default=None)
    types: list[TypeInfo] | None = Field(default=None)


class PoiResponse(BaseModel):
    err: int
    poilist: list[LocationInfo]


def search_poi_raw(area_id: int, name: str | None = None, type_id: int = 0, page: int = 1) -> str | Exception:
    """
    ヤマレコの地名データを検索する

    Args:
        name: 検索したい地名（2文字以上で部分一致）
        area_id: エリアID（0で全エリア）
        type_id: データ種別（0で全種別、1=山頂、2=峠、3=分岐、4=登山口、6=山小屋、10=危険個所）

    Returns:
        生jsonテキスト
    """
    data = {
        "name": name,
        "area_id": area_id,
        "page": page,
        "type_id": type_id,
    }
    res = httpx.post("https://api.yamareco.com/api/v1/searchPoi", data=data)
    try:
        res.raise_for_status()
    except Exception as e:
        return e

    return res.text


def search_poi(area_id: int, name: str | None = None, type_id: int = 0) -> list[dict]:
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
    r = httpx.post("https://api.yamareco.com/api/v1/searchPoi", data=data)
    result = r.json()
    if result.get("err") == 0 and "poilist" in result:
        return result["poilist"]
    return []


def search_and_print(area_id: int, name: str) -> None:
    """検索して結果を表示"""
    results = search_poi(area_id, name)
    if results:
        print(f"✓ {name} (area_id={area_id}): {len(results)}件")
        for poi in results[:3]:
            print(f"    - {poi['name']} ({poi.get('elevation', '?')}m) [{poi.get('lat')}, {poi.get('lon')}]")
            print(" | ".join([f"{key}: {value}" for key, value in poi.items()]))

    else:
        print(f"✗ {name} (area_id={area_id}): 見つからず")


def test_poi():
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
        search_and_print(area_id, name)
        print()


if __name__ == "__main__":
    search_and_print(306, "上川乗")
