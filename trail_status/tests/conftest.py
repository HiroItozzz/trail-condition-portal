"""
pytest設定とテスト共通フィクスチャ
"""

import pytest
import os
from pathlib import Path

# pytest-asyncio設定
pytest_plugins = ["pytest_asyncio"]

# Django設定
pytest_plugins = ["pytest_django"]


@pytest.fixture
def mock_api_keys(monkeypatch):
    """API キーをモック設定（全テスト共通）"""
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-deepseek-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-gemini-key')


@pytest.fixture
def clean_env(monkeypatch):
    """環境変数をクリア"""
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)


@pytest.fixture
def sample_llm_config():
    """共通のLLM設定"""
    return {
        "prompt": "テスト用プロンプト",
        "model": "deepseek-chat",
        "temperature": 0.3,
        "data": "テスト用データ"
    }


@pytest.fixture
def sample_prompt_data():
    """テスト用プロンプトとデータ"""
    return {
        "prompt": "テスト用プロンプト",
        "data": "テスト用データ"
    }


@pytest.fixture
def mock_openai_response():
    """OpenAI APIレスポンスのモック"""
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"conditions": []}'
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.completion_tokens_details.reasoning_tokens = 0
    
    return mock_response


@pytest.fixture
def mock_gemini_response():
    """Gemini APIレスポンスのモック"""
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.text = '{"conditions": []}'
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.thoughts_token_count = 20
    mock_response.usage_metadata.candidates_token_count = 50
    
    return mock_response


# Django settings for test
@pytest.fixture(scope="session")
def django_db_setup():
    """テスト用データベース設定"""
    pass


# 非同期テスト用の設定
@pytest.fixture(scope="session")
def event_loop_policy():
    """非同期テスト用のイベントループポリシー"""
    import asyncio
    return asyncio.WindowsProactorEventLoopPolicy() if os.name == 'nt' else asyncio.DefaultEventLoopPolicy()