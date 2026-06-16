"""
LlmConfig設定クラスのテスト
"""

from unittest.mock import MagicMock

import pytest
import yaml

from trail_status.services import prompt_utils
from trail_status.services.llm_client import LlmConfig
from trail_status.services.prompt_utils import PromptFile


def test_valid_config(mock_api_keys):
    """正常な設定でのインスタンス化テスト"""
    config = LlmConfig(site_prompt="テストプロンプト", model="deepseek-chat", temperature=0.5, data="テストデータ")
    assert config.site_prompt == "テストプロンプト"
    assert config.model == "deepseek-chat"
    assert config.temperature == 0.5
    assert config.api_key == "test-deepseek-key"


def test_invalid_model_pattern():
    """不正なモデル名でのバリデーションテスト"""
    with pytest.raises(ValueError):
        LlmConfig(site_prompt="テストプロンプト", model="invalid-model", data="テストデータ")


def test_invalid_temperature_range():
    """不正な温度値でのバリデーションテスト"""
    with pytest.raises(ValueError):
        LlmConfig(
            site_prompt="テストプロンプト",
            model="deepseek-chat",
            temperature=3.0,  # 範囲外
            data="テストデータ",
        )


def test_api_key_auto_detection_deepseek(mock_api_keys):
    """DeepSeekモデルでのAPIキー自動取得テスト"""
    config = LlmConfig(site_prompt="テストプロンプト", model="deepseek-reasoner", data="テストデータ")
    assert config.api_key == "test-deepseek-key"


def test_api_key_auto_detection_gemini(mock_api_keys):
    """GeminiモデルでのAPIキー自動取得テスト"""
    config = LlmConfig(site_prompt="テストプロンプト", model="gemini-3-flash-preview", data="テストデータ")
    assert config.api_key == "test-gemini-key"


def test_api_key_missing_error(no_api_keys):
    """APIキー未設定時のエラーテスト"""
    config = LlmConfig(site_prompt="テストプロンプト", model="deepseek-chat", data="テストデータ")
    with pytest.raises(ValueError, match="環境変数 DEEPSEEK_API_KEY が設定されていません"):
        _ = config.api_key


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
        self.mock_config = MagicMock(return_value=PromptFile(**self.individual_config))
        self.mock_template = MagicMock(return_value=PromptFile(**self.template_config))
        self.data = "テスト登山道A: 通行止め"


class TestFromFile(SetUp):
    def test_from_file_load_config(self, monkeypatch):
        monkeypatch.setattr(PromptFile, "load_site_config", self.mock_config)
        filename = "test_config.yaml"

        result = LlmConfig.from_file(filename, self.data)

        self.mock_config.assert_called_once_with(filename)

        assert result.site_prompt == self.individual_config["prompt"]
        assert result.model == self.individual_config["config"]["model"]
        assert result.temperature == self.individual_config["config"]["temperature"]
        assert result.thinking_budget == self.individual_config["config"]["thinking_budget"]


class TestReadConfig(SetUp):
    def test_use_template_False(self, tmp_path, monkeypatch):
        """use_template=Falseの場合の結合テスト"""
        self.individual_config["config"]["use_template"] = False

        monkeypatch.setattr(prompt_utils, "get_prompt_dir", MagicMock(return_value=tmp_path))
        template_path = tmp_path / "template.yaml"
        template_path.write_text(yaml.safe_dump(self.template_config), encoding="utf-8")
        individual_path = tmp_path / "individual.yaml"
        individual_path.write_text(yaml.safe_dump(self.individual_config), encoding="utf-8")

        config = LlmConfig.from_file(individual_path.name, self.data)

        assert config.full_prompt == self.individual_config["prompt"]
        assert config.thinking_budget == self.individual_config["config"]["thinking_budget"]
        assert config.temperature == self.individual_config["config"]["temperature"]

    def test_use_template_True(self, tmp_path, monkeypatch):
        """use_template=Trueの場合の結合テスト"""

        monkeypatch.setattr(prompt_utils, "get_prompt_dir", MagicMock(return_value=tmp_path))
        template_path = tmp_path / "template.yaml"
        template_path.write_text(yaml.safe_dump(self.template_config), encoding="utf-8")
        individual_path = tmp_path / "individual.yaml"
        individual_path.write_text(yaml.safe_dump(self.individual_config), encoding="utf-8")

        config = LlmConfig.from_file(individual_path.name, self.data)

        expected_prompt = self.template_config["prompt"] + "\n\n" + self.individual_config["prompt"]
        assert config.full_prompt == expected_prompt
        assert config.thinking_budget == self.individual_config["config"]["thinking_budget"]
        assert config.temperature == self.individual_config["config"]["temperature"]
