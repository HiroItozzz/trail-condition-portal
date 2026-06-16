from unittest.mock import MagicMock

import pytest
import yaml

from trail_status.services import prompt_utils
from trail_status.services.prompt_utils import PromptFile


class SetUp:
    def setup_method(self):
        self.template_config = {
            "prompt": "テストプロンプト",
            "config": {"model": "gemini-test-template", "temperature": 1.8, "thinking_budget": 20000},
        }
        self.individual_config = {
            "prompt": "個別プロンプト",
            "config": {"model": "gpt-test-individual", "temperature": 0.2, "thinking_budget": 50, "use_template": True},
        }

    def teardown_method(self):

        PromptFile.load_template.cache_clear()


class TestUtils(SetUp):
    def test_load_site_and_template_confg(self, tmp_path, monkeypatch):
        """プロンプトファイル読み込みのテスト"""
        monkeypatch.setattr(prompt_utils, "get_prompt_dir", MagicMock(return_value=tmp_path))
        template_path = tmp_path / "template.yaml"
        template_path.write_text(yaml.safe_dump(self.template_config), encoding="utf-8")
        individual_path = tmp_path / "individual.yaml"
        individual_path.write_text(yaml.safe_dump(self.individual_config), encoding="utf-8")

        individual_result = PromptFile.load_site_config(individual_path.name)
        template_result = PromptFile.load_template(template_path)

        assert individual_result == PromptFile(**self.individual_config)
        assert template_result == PromptFile(**self.template_config)
