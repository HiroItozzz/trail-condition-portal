import logging
import unicodedata
from functools import lru_cache

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Reconciler:
    def _calculate_similarity(self, existing, new_data) -> float:
        """
        複数フィールドを組み合わせた類似度スコア（0.0 ~ 1.0）

        Args:
            existing: 既存のDBレコード
            new_data: AIが抽出した新規データ

        Returns:
            類似度スコア（0.0 = 完全不一致、1.0 = 完全一致）
        """
        # 1. 山名の類似度
        mountain_score = (
            fuzz.token_set_ratio(
                existing.mountain_name_raw,
                new_data.mountain_name_raw,
                processor=lambda s: self.decompose_text(s, noun_only=True),
                score_cutoff=0.6,
            )
            / 100.0
        )

        # 2. 登山道名の類似度
        trail_score = (
            fuzz.WRatio(
                existing.trail_name,
                new_data.trail_name,
                processor=lambda s: self.decompose_text(s, noun_only=False),
                score_cutoff=0.5,
            )
            / 100.0
        )

        # 3. タイトルの類似度
        title_score = (
            fuzz.WRatio(
                existing.title,
                new_data.title,
                processor=lambda s: self.decompose_text(s, noun_only=False),
                score_cutoff=0.5,
            )
            / 100.0
        )

        # 4. 詳細説明の類似度（トークンセット比較）
        if existing.description and new_data.description:
            # 両方ある場合: 4フィールド使用
            _existing_des = existing.description[: self.DESC_COMPARE_LENGTH]
            _new_des = new_data.description[: self.DESC_COMPARE_LENGTH]
            # 詳細説明の長さで場合分け
            if len(_existing_des) <= 20 and len(_new_des) <= 20:
                desc_score = (
                    fuzz.token_set_ratio(
                        _existing_des,
                        _new_des,
                        processor=lambda s: self.decompose_text(s, noun_only=False),
                        score_cutoff=0.8,
                    )
                    / 100.0
                )
            else:
                desc_score = (
                    fuzz.partial_token_set_ratio(
                        _existing_des,
                        _new_des,
                        processor=lambda s: self.decompose_text(s, noun_only=False),
                        score_cutoff=0.6,
                    )
                    / 100.0
                )

            base_score = (
                mountain_score * self.FIELD_WEIGHT_MOUNTAIN
                + trail_score * self.FIELD_WEIGHT_TRAIL
                + title_score * self.FIELD_WEIGHT_TITLE
                + desc_score * self.FIELD_WEIGHT_DESC
            )
        else:
            # descriptionがない場合: 3フィールドに重み再配分
            base_score = (
                mountain_score * self.FIELD_WEIGHT_MOUNTAIN_NO_DESC
                + trail_score * self.FIELD_WEIGHT_TRAIL_NO_DESC
                + title_score * self.FIELD_WEIGHT_TITLE_NO_DESC
            )

        # ボーナス1: statusが一致
        if existing.status == new_data.status:
            base_score = min(1.0, base_score + self.BONUS_STATUS_MATCH)

        # ボーナス2: 登録日が近い
        if new_data.reported_at and existing.created_at:
            days_diff = abs((existing.created_at.date() - new_data.reported_at).days)
            if days_diff <= self.DATE_PROXIMITY_DAYS:
                base_score = min(1.0, base_score + self.BONUS_DATE_PROXIMITY)

        return base_score

    @lru_cache
    def decompose_text(self, text: str, noun_only: bool = False) -> str:
        """テキストの形態素解析をしトークンごとに分かち書きした文字列を返却

        - token_set_ratio, token_sort_ratio用
        """
        normalized = self.normalize_text(text)
        tokens = []
        for m in self.sudachi.tokenize(normalized, self.SPLIT_MODE):
            pos = m.part_of_speech()
            if noun_only and pos[0] != "名詞":
                continue
            tokens.append(m.surface())

        if not tokens:
            logger.warning("トークンが空です。原文を返却します。")
            return normalized
        return " ".join(tokens)

    @staticmethod
    def normalize_text(text: str) -> str:
        """全角半角・空白を揃えて比較の精度を上げる"""
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text).strip().replace(" ", "").replace("　", "")
