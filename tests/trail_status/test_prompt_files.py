"""
本物のプロンプトファイルを読み込むテスト

`test_prompt_utils.py` は tmp_path 上のダミーの YAML を使うが、こちらは
`trail_status/services/prompts/` の本物のファイルを読む。本番バッチより先に
キーの書き間違いや `LlmConfig` が作れない設定に気づけるようにする。
"""

from pathlib import Path

import pytest
import yaml
from pydantic.alias_generators import to_camel

from trail_status.services import prompt_utils
from trail_status.services.llm_client import LlmConfig
from trail_status.services.prompt_utils import PromptFile, PromptFileConfig
from trail_status.services.types import LlmModel

# 対象は数字3桁+アンダースコアで始まるファイル（example.yaml等のテンプレート・サンプルは除く）
TARGET_FILES: list[Path] = sorted(prompt_utils.get_prompt_dir().glob("[0-9][0-9][0-9]_*.yaml"))

# キーの確認では、個別のファイルに加えてtemplate.yamlも対象にする
# （個別のファイルの多くはmodel/temperature/thinking_budgetが空で、実際の値はテンプレートが決めるため）
TARGET_FILES_WITH_TEMPLATE: list[Path] = [
    *TARGET_FILES,
    prompt_utils.get_prompt_dir() / "template.yaml",
]


class TestPromptFiles:
    """対象のプロンプトファイルが正しく読み込めることの確認"""

    def test_target_files_found(self):
        """対象のファイルが1件以上見つかる

        parametrizeの値が空だとテストがskipになり、何も確かめずに通ってしまうため、
        対象が見つかること自体は別のテストで確認する。
        """
        assert len(TARGET_FILES) >= 1

    @pytest.mark.parametrize("path", TARGET_FILES_WITH_TEMPLATE, ids=[p.name for p in TARGET_FILES_WITH_TEMPLATE])
    def test_keys_are_known(self, path):
        """YAMLのキーに書き間違いがないことを確認する

        PromptFileは知らないキーを黙って無視するため、safe_loadした辞書のキーを
        直接見て気づけるようにする。use_templateが無効でない情報源の設定の元になるtemplate.yamlも対象にする。
        """
        config_dict = yaml.safe_load(path.read_text(encoding="utf-8"))

        assert set(config_dict.keys()) <= {"prompt", "config"}

        known_config_keys = set(PromptFileConfig.model_fields) | {
            to_camel(name) for name in PromptFileConfig.model_fields
        }
        if config_dict.get("config"):
            assert set(config_dict["config"].keys()) <= known_config_keys

    @pytest.mark.parametrize("path", TARGET_FILES, ids=[p.name for p in TARGET_FILES])
    def test_load_merged_config_builds_llm_config(self, path, mock_api_keys):
        """テンプレートと合わせてLlmConfigが例外なく作れることを確認する

        temperatureの範囲はLlmConfigのバリデーションで確かめられるが、モデル名は
        `gemini-`などの頭しか見ていないため、LlmModelのどれかと一致することはここで確かめる。
        """
        prompt_file = PromptFile.load_merged_config(path.name, url="https://example.com/")
        config = LlmConfig.from_file(prompt_file, data="テスト")

        assert config.model in set(LlmModel)
        assert config.prompt != ""
        assert config.prompt_filename == path.name
