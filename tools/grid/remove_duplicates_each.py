"""
POIデータの重複除去

samples/raw/ 以下の指定のフォルダの各JSONファイルを読み込み、(lat, lng) をキーに
重複を除去して親ディレクトリの各ファイルに出力する。

コマンド:
uv run python -m tools.grid.remove_duplicates_each
"""

import json
from pathlib import Path

AREA_NAME = "okuchichibu"

INPUT_DIR = Path.cwd() / "tools/grid/samples/raw"
FILES: list = INPUT_DIR.glob("*_mountaintop.json")

for file in FILES:
    data = json.loads(file.read_text())
    print(f"処理開始: {file.name}\n件数: {len(data)}件")
    output_data = []
    grids = set()
    for place in data:
        grid = (place["lat"], place["lng"])
        if grid not in grids:
            output_data.append(place)
        grids.add(grid)
    out_json = json.dumps(output_data, ensure_ascii=False, indent=2)

    (INPUT_DIR.parent / file.name).write_text(out_json, encoding="utf-8")
    print(f"処理後件数: {len(grids)}件")


# 奥多摩: 2289件
# 丹沢:   1134件
# 奥武蔵: 1669件
# 奥秩父: 1121件
