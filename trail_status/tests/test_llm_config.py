"""
LlmConfig設定クラスのテスト
"""

import pytest

from trail_status.services.llm_client import LlmConfig


class TestLlmConfig:
    """LlmConfig設定クラスのテスト"""
    
    def test_valid_config(self, mock_api_keys):
        """正常な設定でのインスタンス化テスト"""
        config = LlmConfig(
            prompt="テストプロンプト",
            model="deepseek-chat",
            temperature=0.5,
            data="テストデータ"
        )
        assert config.prompt == "テストプロンプト"
        assert config.model == "deepseek-chat"
        assert config.temperature == 0.5
        assert config.api_key == "test-deepseek-key"

    def test_invalid_model_pattern(self):
        """不正なモデル名でのバリデーションテスト"""
        with pytest.raises(ValueError):
            LlmConfig(
                prompt="テストプロンプト",
                model="invalid-model",
                data="テストデータ"
            )

    def test_invalid_temperature_range(self):
        """不正な温度値でのバリデーションテスト"""
        with pytest.raises(ValueError):
            LlmConfig(
                prompt="テストプロンプト",
                model="deepseek-chat",
                temperature=3.0,  # 範囲外
                data="テストデータ"
            )
    
    def test_api_key_auto_detection_deepseek(self, mock_api_keys):
        """DeepSeekモデルでのAPIキー自動取得テスト"""
        config = LlmConfig(
            prompt="テストプロンプト",
            model="deepseek-reasoner",
            data="テストデータ"
        )
        assert config.api_key == "test-deepseek-key"
    
    def test_api_key_auto_detection_gemini(self, mock_api_keys):
        """GeminiモデルでのAPIキー自動取得テスト"""
        config = LlmConfig(
            prompt="テストプロンプト", 
            model="gemini-3-flash-preview",
            data="テストデータ"
        )
        assert config.api_key == "test-gemini-key"
    
    def test_api_key_missing_error(self, clean_env):
        """APIキー未設定時のエラーテスト"""
        config = LlmConfig(
            prompt="テストプロンプト",
            model="deepseek-chat",
            data="テストデータ"
        )
        with pytest.raises(ValueError, match="環境変数 DEEPSEEK_API_KEY が設定されていません"):
            _ = config.api_key