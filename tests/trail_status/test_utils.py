import copy
from collections import namedtuple
from unittest.mock import MagicMock

import pytest
import yaml

from trail_status.services import prompt_utils
from trail_status.services.prompt_utils import PromptFile


@pytest.fixture
def _mock_config():
    template_config = {
        "prompt": "テストプロンプト",
        "config": {"model": "gemini-test-template", "temperature": 1.8, "thinking_budget": 20000},
    }
    individual_config = {
        "prompt": "個別プロンプト",
        "config": {"model": "gpt-test-individual", "temperature": 0.2, "thinking_budget": 50, "use_template": True},
    }
    Config = namedtuple("Config", ["template", "individual"])

    return Config(template_config, individual_config)


@pytest.fixture
def mock_config(_mock_config, tmp_path, monkeypatch):
    monkeypatch.setattr(prompt_utils, "get_prompt_dir", MagicMock(return_value=tmp_path))
    template_path = tmp_path / "template.yaml"
    template_path.write_text(yaml.safe_dump(_mock_config.template), encoding="utf-8")
    individual_path = tmp_path / "individual.yaml"
    individual_path.write_text(yaml.safe_dump(_mock_config.individual), encoding="utf-8")

    Paths = namedtuple("Paths", ["template", "individual"])

    return _mock_config, Paths(template_path, individual_path)


class TestUtils:
    def test_load_site_config(self, mock_config):
        """プロンプトファイル読み込みのテスト"""
        config, paths = mock_config
        result = PromptFile.load_site_config(paths.individual.name)
        assert result == PromptFile(**config.individual)

    def test_load_site_and_template_config(self, mock_config):
        """プロンプトファイル読み込みのテスト"""
        config, paths = mock_config
        result = PromptFile.load_template(paths.template.name)

        assert result == PromptFile(**config.template)

    def test_load_merged_config(self, mock_config):
        config, paths = mock_config
        # プロンプトは結合
        expected_prompt = config.template["prompt"] + "\n\n" + config.individual["prompt"]

        expected_config = copy.deepcopy(config.individual)
        expected_config["prompt"] = expected_prompt
        expected_config["filename"] = paths.individual.name

        result = PromptFile.load_merged_config(paths.individual.name)

        assert result == PromptFile(**expected_config)
