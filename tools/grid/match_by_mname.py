import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, TypeAdapter
from rapidfuzz import fuzz
from sudachipy import Dictionary, SplitMode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# fmt: off

INPUT_PATH = Path().cwd() / r"""
E:\Dev\Projects\trail-condition-portal\trail_status\services\sample\001_okutama_vc\gpt-5-mini_20260114_143037.json
""".strip()

GRIDDATA_DIR = Path.cwd() / """
tools/grid/samples/Okutama_mountaintop.json
""".strip()

# fmt: on


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


class GridSearch:
    FIELD_WEIGHT_MOUNTAIN = 1.0
    FIELD_WEIGHT_TRAIL = 0.5
    threshold = 0.3

    Analyzer = Dictionary(dict="full").create()

    SPLIT_MODE = SplitMode.C

    def __init__(self, grids):
        self.grids = grids

    def get_similar_data(self, cons: ConditionList) -> dict:
        results = {}
        for con in cons:
            results[(con.trail_name, con.mountain_name_raw)] = self.calculate_similarity(con)

        return results

    def calculate_similarity(self, con: Condition) -> list:

        result: list[tuple[str, int]] = []

        for grid in self.grids:
            # 1. 山名の類似度
            mountain_score = (
                fuzz.ratio(
                    con.mountain_name_raw,
                    grid.title,
                    processor=lambda s: self.decompose_text(s, noun_only=True),
                    score_cutoff=0,
                )
                / 100.0
            )

            # 2. 登山道名の類似度
            trail_score = (
                fuzz.WRatio(
                    con.trail_name,
                    grid.title,
                    processor=lambda s: self.decompose_text(s, noun_only=False),
                    score_cutoff=0,
                )
                / 100.0
            )

            score = (
                mountain_score * self.FIELD_WEIGHT_MOUNTAIN  # + trail_score * self.FIELD_WEIGHT_TRAIL
                # + desc_score * self.FIELD_WEIGHT_DESC
            )
            if score >= self.threshold:
                result.append((grid, score))

        return sorted(result, key=lambda x: x[1], reverse=True)[:3]

    @lru_cache
    def decompose_text(self, text: str, noun_only: bool = False) -> str:
        """テキストの形態素解析をしトークンごとに分かち書きした文字列を返却

        - token_set_ratio, token_sort_ratio用
        """
        normalized = self.normalize_text(text)
        tokens = []
        for m in self.Analyzer.tokenize(normalized, self.SPLIT_MODE):
            pos = m.part_of_speech()
            if noun_only and pos[0] != "名詞":
                continue
            tokens.append(m.surface())

        if not tokens:
            # logger.warning("トークンが空です。原文を返却します。")
            return normalized
        return " ".join(tokens)

    @staticmethod
    def normalize_text(text: str) -> str:
        """全角半角・空白を揃えて比較の精度を上げる"""
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text).strip().replace(" ", "").replace("　", "")


def get_result(threshold: float = 0.7):
    """固定閾値による結果を一つ取得する."""
    grids = TypeAdapter(list[GridData]).validate_json(GRIDDATA_DIR.read_text(encoding="utf-8"))
    res = ConditionList.model_validate_json(INPUT_PATH.read_text(encoding="utf-8"))
    cons = res.conditions

    tool = GridSearch(grids)

    results = tool.get_similar_data(cons)

    output_text = ""
    for con, candidates in results.items():
        title_text_1 = f"\n---対象データ---\n{con}"
        title_text_2 = "---候補データ---"
        print(title_text_1)
        print(title_text_2)
        output_text += title_text_1 + "\n" + title_text_2 + "\n"
        for candidate, score in candidates:
            candidate_text = f"{candidate} スコア: {score}"
            print(candidate_text)
            output_text += candidate_text + "\n"

    result_path = Path.cwd() / "tools/grid/matching_result.txt"
    result_path.write_text(output_text, encoding="utf-8")


def analyze_results():
    """各閾値に対して同定成功件数のdfを返却する"""
    grids = TypeAdapter(list[GridData]).validate_json(GRIDDATA_DIR.read_text(encoding="utf-8"))
    res = ConditionList.model_validate_json(INPUT_PATH.read_text(encoding="utf-8"))

    cons = res.conditions
    tool = GridSearch(grids)

    thresholds = np.arange(0.1, 0.9, 0.1)

    output_data = []
    for t in thresholds:
        tool.threshold = t
        cnt = 0
        results = tool.get_similar_data(cons)
        for _, candidates in results.items():
            if not candidates:
                continue
            max_score = max((y for x, y in candidates))
            max_score_items = [x for x, y in candidates if y == max_score]
            if len(max_score_items) == 1:
                cnt += 1
        output_data.append(
            {
                "threshold": t,
                "count": cnt,
                "total": len(cons),
                "rate": cnt / len(cons),
            }
        )

    df = pd.DataFrame(output_data, index=thresholds)

    return df


if __name__ == "__main__":
    #print(analyze_results())

    get_result()
