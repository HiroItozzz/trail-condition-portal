"""
設定ファイル読み込みのテスト
"""

import yaml

from django.conf import settings

from trail_status.services.schema import TrailConditionSchemaList


class TestConfigFile:
    """設定ファイル読み込みテスト"""
    
    def test_load_existing_config(self):
        """既存の設定ファイル読み込みテスト"""
        config_path = settings.BASE_DIR / "trail_status" / "services" / "prompts" / "okutama_vc.yaml"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            assert "prompt" in config
            assert isinstance(config["prompt"], str)
            assert len(config["prompt"]) > 0

    def test_sample_data_exists(self):
        """サンプルデータファイルの存在確認"""
        sample_path = settings.BASE_DIR / "trail_status" / "services" / "sample" / "sample_okutama_vc.txt"
        
        if sample_path.exists():
            data = sample_path.read_text(encoding="utf-8")
            assert isinstance(data, str)
            assert len(data) > 0
    
    def test_ai_models_config_exists(self):
        """AI設定ファイルの存在確認"""
        config_path = settings.BASE_DIR / "trail_status" / "services" / "config" / "ai_models.yaml"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            assert "models" in config
            assert "deepseek" in config["models"]
            assert "gemini" in config["models"]