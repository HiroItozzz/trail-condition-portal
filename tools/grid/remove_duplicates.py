"""
POIデータの重複除去

all_types/ 以下の指定のフォルダの全JSONファイルを読み込み、(lat, lng) をキーに
重複を除去して1ファイルにまとめる。
"""

import json
from pathlib import Path

AREA_NAME = "okuchichibu"

INPUT_DIR = Path.cwd() / "tools/grid/samples/all_types" / AREA_NAME.capitalize()
FILES: list = INPUT_DIR.glob("*")
OUTPUT_PATH = Path.cwd() / f"tools/grid/samples/All_places_{AREA_NAME.upper()}.json"

output_data = []
grids = set()

for file in FILES:
    for place in json.loads(file.read_text()):
        grid = (place["lat"], place["lng"])
        if grid not in grids:
            output_data.append(place)
        grids.add(grid)

out_json = json.dumps(output_data, ensure_ascii=False, indent=2)
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_PATH.write_text(out_json, encoding="utf-8")
print(f"総件数: {len(grids)}件")

# 奥多摩: 2289件
# 丹沢:   1134件
# 奥武蔵: 1669件
# 奥秩父: 1121件
