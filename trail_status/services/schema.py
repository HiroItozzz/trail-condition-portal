from datetime import date

from pydantic import BaseModel, Field

from ..models.condition import StatusType
from ..models.mountain import AreaName


class TrailConditionSchemaAi(BaseModel):
    """
    AIに構造化出力を指定するスキーマの各項目
    ※重要：descriptionはAIが読むプロンプト部分
    """

    trail_name: str = Field(description="登山道名・区間（原文そのまま）")
    mountain_name_raw: str = Field(
        default="",
        description="山名（原文そのまま / 原文がなければ該当する妥当な山名を推測 / 推測不可能であれば空文字）",
    )
    title: str = Field(description="登山道状況タイトル（原文そのまま）")
    description: str = Field(
        default="",
        description="状況詳細説明（原文そのまま / 該当する記述がなければ空文字）",
    )
    reported_at: date | None = Field(
        default=None,
        description="報告日（YYYY-MM-DD形式） / 該当項目がない、あるいはわからなければ、None型",
    )
    resolved_at: date | None = Field(
        default=None,
        description="解消日（YYYY-MM-DD形式） / 過去の該当登山道状況の問題がすでに解消されたことが分かる場合、あるいは解消される予定日の記述がある場合に入力",
    )
    status: StatusType = Field(
        max_length=20,
        description="最も適する状況種別を選択",
    )
    area: AreaName = Field(
        max_length=20,
        description="最も該当する山域を選択",
    )  # 例: 奥多摩
    reference_URL: str = Field(default="", max_length=500, description="補足URL / pdf等参照先URLがあれば記述")
    comment: str = Field(default="", description="備考欄 / 状況詳細説明から漏れる情報があれば自由記述")


class TrailConditionSchemaList(BaseModel):
    """AIでの構造化出力を指定するスキーマ"""

    trail_condition_records: list[TrailConditionSchemaAi] = Field(description="登山道状況のリスト")


class TrailConditionSchemaInternal(TrailConditionSchemaAi):
    """DjangoのTrailConditionモデルに保存する内容と完全に一致するクラス"""

    url1: str
    ai_config: dict
    mountain_group: str | None = Field(default=None, description="山グループ / 後で手動入力")
