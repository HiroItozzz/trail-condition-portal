"""
ヤマレコPOIデータ 全件取得バッチ

エリア×種別の全組み合わせでPOIデータを取得し、
samples/ ディレクトリにJSONファイルとして保存する。
all_types=Trueの場合、指定のエリアのすべてのタイプの地名リストを取得する.
"""

import json
import time
from pathlib import Path

from pydantic import ValidationError

from tools.grid.yamareco_poi import PoiResponse, search_poi_raw

OUTPUT_DIR = Path.cwd() / "tools/grid/samples"

# タイプID一覧
_TYPE_IDS = {
    "1": "山頂",
    "2": "峠",
    "3": "分岐",
    "4": "登山口",
    "5": "テント場",
    "6": "山小屋",
    "7": "水場",
    "8": "食事",
    "9": "お風呂",
    "10": "危険個所",
    "11": "展望ポイント",
    "12": "バス停",
    "13": "駐車場",
    "14": "トイレ",
    "15": "登山ポスト",
    "16": "滝",
    "17": "駅",
    "18": "他の宿泊施設",
}

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

AREA_CONSTANTS = {
    "OKUTAMA": {
        "filename_key": "Okutama",
        "area_key": 306,
    },
    "TANZAWA": {
        "filename_key": "Tanzawa",
        "area_key": 307,
    },
    "OKUMUSASHI": {
        "filename_key": "Okumusashi",
        "area_key": 305,
    },
    "OKUCHICHIBU": {
        "filename_key": "Okuchichibu",
        "area_key": 310,
    },
}

TYPE_CONSTANTS = {
    "山頂": {
        "filename_key": "mountaintop",
        "type_id": 1,
    },
    "登山口": {
        "filename_key": "trailhead",
        "type_id": 4,
    },
    "バス停": {
        "filename_key": "busstop",
        "type_id": 12,
    },
}


TYPE_CONSTANTS_ALL = {
    "山頂": {"filename_key": "mountaintop", "type_id": 1},
    "峠": {"filename_key": "pass", "type_id": 2},
    "分岐": {"filename_key": "junction", "type_id": 3},
    "登山口": {"filename_key": "trailhead", "type_id": 4},
    "テント場": {"filename_key": "campsite", "type_id": 5},
    "山小屋": {"filename_key": "mountain_hut", "type_id": 6},
    "水場": {"filename_key": "water", "type_id": 7},
    "食事": {"filename_key": "restaurant", "type_id": 8},
    "お風呂": {"filename_key": "bath", "type_id": 9},
    "危険個所": {"filename_key": "danger", "type_id": 10},
    "展望ポイント": {"filename_key": "viewpoint", "type_id": 11},
    "バス停": {"filename_key": "busstop", "type_id": 12},
    "駐車場": {"filename_key": "parking", "type_id": 13},
    "トイレ": {"filename_key": "restroom", "type_id": 14},
    "登山ポスト": {"filename_key": "registration", "type_id": 15},
    "滝": {"filename_key": "waterfall", "type_id": 16},
    "駅": {"filename_key": "station", "type_id": 17},
    "他の宿泊施設": {"filename_key": "accommodation", "type_id": 18},
}


def get_all_poi(type_id: int, area_id: int = 306):
    responses = []
    for i in range(100):
        res_text = search_poi_raw(
            area_id,
            type_id=type_id,
            page=i,
        )
        if isinstance(res_text, Exception):
            print(f"HTTPエラー発生。詳細：{res_text}")
            break
        try:
            res = PoiResponse.model_validate_json(res_text)
        except ValidationError:
            print("クライアントエラー発生。最終ページに到達したようです。")
            break

        responses.extend(res.poilist)
        print(f"{i}ページ目取得完了")
        time.sleep(0.2)
    return responses


def main(*areas, all_types: bool = False):

    type_constants = TYPE_CONSTANTS_ALL if all_types else TYPE_CONSTANTS
    # 全タイプ取得の場合エリアを限定、フォルダ変更
    output_dir = OUTPUT_DIR / "all_types" if all_types else OUTPUT_DIR
    area_constants = (
        {key: value for key, value in AREA_CONSTANTS.items() if key in areas} if all_types else AREA_CONSTANTS
    )

    output_dir.mkdir(exist_ok=True)
    for type, type_dict in type_constants.items():
        for area, area_dict in area_constants.items():
            output_path = output_dir / f"{area_dict['filename_key']}_{type_dict['filename_key']}.json"
            responses = get_all_poi(type_dict["type_id"], area_dict["area_key"])

            output_path.write_text(
                json.dumps([r.model_dump() for r in responses], ensure_ascii=False, indent=2),
            )
            print(f"{area}の{type}情報の保存完了")


if __name__ == "__main__":
    # uv run python -m tools.grid.save_poi
    areas = ["OKUCHICHIBU"]
    main(*areas, all_types=True)
