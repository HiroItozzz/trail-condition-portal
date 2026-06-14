from __future__ import annotations

import typing

from django.conf import settings

from .types import SourceSchemaSingle

if typing.TYPE_CHECKING:
    from pathlib import Path


def get_sample_dir() -> Path:
    """sampleディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "sample"


def get_prompts_dir() -> Path:
    """promptsディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "prompts"


def get_prompt_filename_from_data(source_data: SourceSchemaSingle) -> str:
    """ソースデータからプロンプトファイル名を取得"""
    # 形式: {id:03d}_{prompt_key}.yaml
    source_id = source_data.id
    prompt_key = source_data.prompt_key
    return f"{source_id:03d}_{prompt_key}.yaml"
