import copy
from collections import namedtuple
from unittest.mock import MagicMock
from urllib.parse import urlparse

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

    def test_site_config_file_not_exists(self, tmp_path):
        dummy_path = tmp_path / "dummy.yaml"
        result = PromptFile.load_site_config(dummy_path)

        result_text = dummy_path.read_text()

        assert result == PromptFile()
        assert dummy_path.exists()
        assert all(s in result_text for s in ["prompt:", "config:", "use_template: true"])

    def test_site_config_config_dict_is_None(self, mock_config):
        _, paths = mock_config
        paths.individual.write_text("")

        result = PromptFile.load_site_config(paths.individual.name)

        assert result == PromptFile()


    def test_load_template(self, mock_config):
        """プロンプトファイル読み込みのテスト"""
        config, paths = mock_config
        result = PromptFile.load_template(paths.template.name)

        assert result == PromptFile(**config.template)

    def test_load_template_not_exists(self):
        """プロンプトファイル読み込みのテスト"""

        with pytest.raises(FileNotFoundError):
            PromptFile.load_template("dummy_path")

    def test_load_template_prompt_not_set(self, mock_config):
        config, paths = mock_config
        del config.template["prompt"]
        with open(paths.template, "w") as f:
            yaml.safe_dump(config.template, f, encoding="utf-8")

        with pytest.raises(ValueError):
            PromptFile.load_template(paths.template.name)

    def test_load_merged_config(self, mock_config):
        config, paths = mock_config

        root_url = "https://dummy.com/"
        url = root_url + "u/r/i/"
        parsed = urlparse(url)

        expected_prompt = (
            config.template["prompt"].format(scheme=parsed.scheme, netloc=parsed.netloc)
            + "\n\n"
            + config.individual["prompt"]
        )

        expected_config = copy.deepcopy(config.individual)
        expected_config["prompt"] = expected_prompt
        expected_config["filename"] = paths.individual.name

        result = PromptFile.load_merged_config(paths.individual.name, url)

        assert result == PromptFile(**expected_config)

    def test_load_merged_config_use_template_false(self, mock_config):
        config, paths = mock_config
        config.individual["config"]["use_template"] = False
        paths.individual.write_text(yaml.safe_dump(config.individual), encoding="utf-8")

        result = PromptFile.load_merged_config(paths.individual, url="dummy")

        assert result == PromptFile(**config.individual)

    def test_str(self, mock_config, capsys):
        _, path = mock_config
        prompt_file = PromptFile.load_merged_config(path.individual.name, url="https://dummy.com/")

        print(prompt_file)

        out, _ = capsys.readouterr()

        expected_words = ["ファイル名", "モデル", "温度", "思考予算", "テンプレートの使用", "プロンプト"]

        assert all(w in out for w in expected_words)
