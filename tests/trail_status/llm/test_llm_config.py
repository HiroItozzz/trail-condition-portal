"""
LlmConfig設定クラスのテスト
"""

from collections import namedtuple
from unittest.mock import MagicMock

import pytest
import yaml

from trail_status.services import prompt_utils
from trail_status.services.llm_client import LlmConfig
from trail_status.services.prompt_utils import PromptFile


def test_valid_config(mock_api_keys):
    """正常な設定でのインスタンス化テスト"""
    config = LlmConfig(prompt="テストプロンプト", model="deepseek-chat", temperature=0.5, data="テストデータ")
    assert config.prompt == "テストプロンプト"
    assert config.model == "deepseek-chat"
    assert config.temperature == 0.5
    assert config.api_key == "test-deepseek-key"


def test_invalid_model_pattern():
    """不正なモデル名でのバリデーションテスト"""
    with pytest.raises(ValueError):
        LlmConfig(prompt="テストプロンプト", model="invalid-model", data="テストデータ")


def test_invalid_temperature_range():
    """不正な温度値でのバリデーションテスト"""
    with pytest.raises(ValueError):
        LlmConfig(
            prompt="テストプロンプト",
            model="deepseek-chat",
            temperature=3.0,  # 範囲外
            data="テストデータ",
        )


def test_api_key_auto_detection_deepseek(mock_api_keys):
    """DeepSeekモデルでのAPIキー自動取得テスト"""
    config = LlmConfig(prompt="テストプロンプト", model="deepseek-reasoner", data="テストデータ")
    assert config.api_key == "test-deepseek-key"


def test_api_key_auto_detection_gemini(mock_api_keys):
    """GeminiモデルでのAPIキー自動取得テスト"""
    config = LlmConfig(prompt="テストプロンプト", model="gemini-3-flash-preview", data="テストデータ")
    assert config.api_key == "test-gemini-key"


def test_api_key_missing_error(no_api_keys):
    """APIキー未設定時のエラーテスト"""
    config = LlmConfig(prompt="テストプロンプト", model="deepseek-chat", data="テストデータ")
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

    def create_file(self, tmp_path):
        template_path = tmp_path / "template.yaml"
        template_path.write_text(yaml.safe_dump(self.template_config), encoding="utf-8")
        individual_path = tmp_path / "individual.yaml"
        individual_path.write_text(yaml.safe_dump(self.individual_config), encoding="utf-8")

        Paths = namedtuple("Paths", ["template", "individual"])

        return Paths(template_path, individual_path)


class TestFromFile(SetUp):
    def test_valid(self, mock_api_keys, tmp_path, monkeypatch):
        """プロンプト読み込みを含む結合テスト"""
        mock_path = self.create_file(tmp_path)
        monkeypatch.setattr(prompt_utils, "get_prompt_dir", MagicMock(return_value=tmp_path))

        result = LlmConfig.from_file(mock_path.individual.name, self.data)

        expected_prompt = self.template_config["prompt"] + "\n\n" + self.individual_config["prompt"]
        assert result.prompt == expected_prompt
        assert result.thinking_budget == self.individual_config["config"]["thinking_budget"]
        assert result.temperature == self.individual_config["config"]["temperature"]
        assert result.api_key == "test-openai-key"
        print(result)