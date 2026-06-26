from __future__ import annotations

import logging
import shutil
import typing
from functools import lru_cache
from urllib.parse import urlparse

import yaml
from django.conf import settings
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .types import LlmModel

if typing.TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def get_sample_dir() -> Path:
    """sampleディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "sample"


def get_prompt_dir() -> Path:
    """promptsディレクトリのパスを取得"""
    return settings.BASE_DIR / "trail_status" / "services" / "prompts"


class PromptFileConfig(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    model: LlmModel | str | None = None
    temperature: float | None = None
    thinking_budget: int | None = None
    use_template: bool | None = None


class PromptFile(BaseModel):
    prompt: str | None = None
    config: PromptFileConfig = PromptFileConfig(use_template=True)
    filename: str | None = None

    @staticmethod
    def _format_url(prompt: str, url: str) -> str:
        parsed = urlparse(url)
        return prompt.format(scheme=parsed.scheme, netloc=parsed.netloc)

    @staticmethod
    def get_filename_from_data(source_id: int, prompt_key: str) -> str:
        """ソースデータからプロンプトファイル名を取得"""
        # 形式: {id:03d}_{prompt_key}.yaml
        return f"{source_id:03d}_{prompt_key}.yaml"

    @classmethod
    def load_merged_config(cls, filename: str, url: str | None) -> PromptFile:
        """個別プロンプトとテンプレートがマージされたLLMのための設定ファイルを返却

        Args:
            filename (str): プロンプト設定ファイル名
            url (str | None): テンプレートファイル内の置換変数に適用するURL

        Returns:
            PromptFile: プロンプトファイルのインスタンス
        """

        template_file = cls.load_template().model_copy(deep=True)
        individual_file = cls.load_site_config(filename)

        use_template = individual_file.config.use_template
        # (use_template=Noneの場合はtemplateへフォールバック)
        if use_template is False:
            return individual_file

        if url is not None:
            template_file.prompt = cls._format_url(template_file.prompt, url)

        template_file.prompt += "\n\n" + individual_file.prompt if individual_file.prompt else ""

        template_config, individual_config = template_file.config, individual_file.config
        template_config.model = individual_config.model if individual_config.model else template_config.model
        template_config.temperature = (
            individual_config.temperature if individual_config.temperature is not None else template_config.temperature
        )
        template_config.thinking_budget = (
            individual_config.thinking_budget
            if individual_config.thinking_budget is not None
            else template_config.thinking_budget
        )

        ####### メタデータ #######
        template_file.filename = filename

        # use_template: 生成過程確認用途。外部では使用されない
        # ここに到達している時点でTrue
        template_config.use_template = True

        return template_file

    @classmethod
    @lru_cache
    def load_template(cls, filename: str = "template.yaml") -> PromptFile:  # TODO: エラーハンドリングの返却型変更
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

        config_dict = yaml.safe_load(template_path.read_text(encoding="utf-8"))

        if "prompt" not in config_dict:
            raise ValueError(f"テンプレートプロンプトが設定されていません: {template_path}")

        return cls(**config_dict)

    @classmethod
    def load_site_config(cls, filename: str) -> PromptFile:
        """個別プロンプトファイルをファイル名から安全に読み込み辞書で返却
            ファイルがなければ作成をする

        Args:
            filename (str): YAMLファイル名（例：001_okutama_vc.yaml）

        Returns:
            dict: 取得したYAMLファイルの辞書 / 値がない場合: `{}`
        """
        prompt_dir = get_prompt_dir()
        prompt_path = prompt_dir / filename

        if not prompt_path.exists():
            logger.warning(f"サイト別プロンプトファイルが見つかりません: {prompt_path}")
            try:
                shutil.copy(prompt_dir / "example.yaml", prompt_path)
                logger.warning(f"プロンプトファイルを作成しました。ファイル名: {filename}")
            except Exception:
                logger.error("サイト別プロンプトファイルの作成に失敗。example.yamlを確認してください")
            return cls()

        config_dict = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))

        if config_dict is None:
            logger.warning(f"サイト別プロンプトに記載がありません。ファイル名: {filename}")
            return cls()

        return cls(**config_dict)

    def __str__(self):
        prompt = self.prompt
        filename = self.filename
        model = self.config.model
        temperature = self.config.temperature
        thinking_budget = self.config.thinking_budget
        use_template = self.config.use_template

        width, _ = shutil.get_terminal_size()
        left = 6
        return (
            f"ファイル名: {filename}".center(width - 5, "─")
            + f"\nAIのモデル: {model}"
            + f"\n温度: {temperature}"
            + f"\n思考予算: {thinking_budget}"
            + f"\nテンプレートの使用: {use_template}"
            + "\n"
            + "─" * left
            + "プロンプト".ljust(width - left - 5, "─")
            + f"\n{prompt}"
        )
