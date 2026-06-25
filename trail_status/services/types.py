from __future__ import annotations

import typing
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from ..models import AreaName, StatusType

if typing.TYPE_CHECKING:
    from .llm_client import LlmConfig
    from .llm_stats import LlmStats
    from .prompt_utils import PromptFile


area_help_text = " / ".join([f"{label}:{name}" for name, label in AreaName.choices])


# fmt: off
class LlmModel(StrEnum):
    GEMINI_2_5_FLASH        = "gemini-2.5-flash"
    GEMINI_2_5_PRO          = "gemini-2.5-pro"
    GEMINI_3_FLASH_PREVIEW  = "gemini-3-flash-preview"
    GEMINI_3_1_FLASH_LITE   = "gemini-3.1-flash-lite"
    GEMINI_3_5_FLASH        = "gemini-3.5-flash"
    GEMINI_FLASH_LATEST     = "gemini-flash-latest"
    DEEPSEEK_CHAT           = "deepseek-chat"
    DEEPSEEK_REASONER       = "deepseek-reasoner"
    GPT_5_MINI              = "gpt-5-mini"
    GPT_5_NANO              = "gpt-5-nano"
# fmt:on


class ConditionSchemaAi(BaseModel):
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
        description="状況詳細説明（基本は原文そのままだが、文の区切りでの改行のみ追加可 / 該当する記述がなければ空文字）",
    )
    reported_at: date | None = Field(
        default=None,
        description="報告日（YYYY-MM-DD形式） / 日付が具体的に明記されている場合にのみ値を入力",
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
        description=f"最も該当する山域を選択。日本語漢字対応表：{area_help_text}",
    )  # 例: 奥多摩
    reference_url: str = Field(default="", max_length=500, description="補足URL / pdf等参照先URLがあれば記述")
    comment: str = Field(default="", description="備考欄 / 状況詳細説明から漏れる情報があれば自由記述")


class ConditionSchemaAiList(BaseModel):
    """
    AIでの構造化出力を指定するスキーマ
    descriptionをAIが読む
    """

    trail_condition_records: list[ConditionSchemaAi] = Field(description="登山道状況のリスト")


class ConditionSchemaAiInternal(ConditionSchemaAi):
    """DjangoのTrailConditionモデルに保存する内容と完全に一致するクラス"""

    url1: str
    ai_config: dict
    ai_model: str = ""
    prompt_file: str = ""
    mountain_group: str | None = Field(default=None, description="山グループ / 後で手動入力")


@dataclass
class SourceSchemaSingle:
    """DjangoモデルのDataSourceから取り出したデータ"""

    id: int
    name: str
    url1: str
    prompt_file: PromptFile
    content_hash: str | None = None


@dataclass
class ResultSingle:
    """AI出力のサマリー"""

    success: bool
    message: str
    new_hash: str | None = None
    scraped_length: int = 0
    content_changed: bool | None = None
    extracted_trail_conditions: ConditionSchemaAiList | None = None
    stats: LlmStats | None = None
    config: LlmConfig | None = None
