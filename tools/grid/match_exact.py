import json
import re
from pathlib import Path

from pydantic import BaseModel, Field, TypeAdapter

INPUT_DIR_BASE = Path.cwd() / "trail_status/services/sample"
FILENAME = "001_okutama_vc/gemini-3-flash-preview_20260317_140505.json"

GRIDDATA_DIR = Path.cwd() / "tools/grid/samples/All_places_OKUTAMA.json"


INPUT_PATH = INPUT_DIR_BASE / FILENAME


class GridData(BaseModel):
    ptid: int
    title: str
    content: str
    lat: float
    lng: float
    elevation: float
    page_url: str


class Condition(BaseModel):
    trail_name: str
    mountain_name_raw: str
    description: str
    comment: str


class ConditionList(BaseModel):
    conditions: list[Condition] = Field(validation_alias="trail_condition_records")


def 抽出条件1(con, grid):
    return con.trail_name == grid.title or con.mountain_name_raw == grid.title


def 抽出条件2(con, grid):
    return grid.title in con.trail_name.split() or grid.title in con.mountain_name_raw.split()


FUNC = 抽出条件2

print(f"using {FUNC.__name__}")


grids = TypeAdapter(list[GridData]).validate_json(GRIDDATA_DIR.read_text(encoding="utf-8"))

res = ConditionList.model_validate_json(INPUT_PATH.read_text(encoding="utf-8"))
data = res.conditions

result = []
for con in data:
    for grid in grids:
        if FUNC(con, grid):
            result.append((con, grid))
        break

print(f"--------一致件数---------\n {len(result)}件 / {len(data)}件")

print("".join([f"---元データ---\n{g}\n---ヤマレコ---\n{d}\n" for g, d in result]))
