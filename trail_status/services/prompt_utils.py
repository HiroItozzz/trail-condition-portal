from __future__ import annotations

import logging
import shutil
import typing
from functools import lru_cache

import yaml
from django.conf import settings

if typing.TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def get_sample_dir() -> Path:
    """sampleディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "sample"


def get_prompt_dir() -> Path:
    """promptsディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "prompts"


def get_prompt_filename_from_data(source_id: int, prompt_key: str) -> str:
    """ソースデータからプロンプトファイル名を取得"""
    # 形式: {id:03d}_{prompt_key}.yaml
    return f"{source_id:03d}_{prompt_key}.yaml"


@lru_cache
def load_template(filename: str = "template.yaml") -> str:
    """
    template.yamlを読み込み辞書で返却

    Args:
        filename: テンプレートプロンプトファイル名（template.yaml）

    Returns:
        str: プロンプト文字列

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        ValueError: プロンプトが設定されていない場合
    """
    template_dir = get_prompt_dir()
    template_path = template_dir / filename

    if not template_path.exists():
        raise FileNotFoundError(f"テンプレートファイルが見つかりません: {template_path}")

    prompt_dict = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    if "prompt" not in prompt_dict:
        raise ValueError(f"テンプレートプロンプトが設定されていません: {template_path}")

    return prompt_dict


def load_site_config(filename: str) -> dict:
    """個別プロンプトファイルをファイル名から安全に読み込み辞書で返却
        ファイルがなければ作成をする

    Args:
        filename (str): YAMLファイル名（例：001_okutama_vc.yaml）

    Returns:
        dict: 取得したYAMLファイルの辞書 / 値がない場合: `{}`
    """
    prompts_dir = get_prompt_dir()
    prompt_path = prompts_dir / filename

    if not prompt_path.exists():
        logger.warning(f"サイト別プロンプトファイルが見つかりません: {prompt_path}")
        try:
            shutil.copy(prompts_dir / "example.yaml", prompt_path)
            logger.warning(f"プロンプトファイルを作成しました。ファイル名: {filename}")
        except Exception:
            logger.error("サイト別プロンプトファイルの作成に失敗。example.yamlを確認してください")
        return {}

    config_dict = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))

    if config_dict is None:
        logger.warning(f"サイト別プロンプトに記載がありません。ファイル名: {filename}")
        return {}

    return config_dict


def to_safe_dict(config_dict: dict) -> dict:
    """Noneを値に持つ辞書のキーを完全排除

    Args:
        config_dict (dict): キーはあるが値未設定の辞書（getメソッドでエラー）

    Returns:
        dict: 安全にgetできる辞書
    """
    if config_dict:
        config_dict = {k: v for k, v in config_dict.items() if v is not None}
    return config_dict
