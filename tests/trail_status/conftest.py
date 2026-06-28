"""
pytest設定とテスト共通フィクスチャ
"""

import os
from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import yaml

from trail_status.services import prompt_utils
from trail_status.services.prompt_utils import PromptFile


@pytest.fixture(autouse=True)
def clear_cache():
    PromptFile.load_template.cache_clear()
    yield


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


@pytest.fixture
def mock_config_template_False(_mock_config, tmp_path, monkeypatch):
    _mock_config.individual["config"]["use_template"] = False

    monkeypatch.setattr(prompt_utils, "get_prompt_dir", MagicMock(return_value=tmp_path))
    template_path = tmp_path / "template.yaml"
    template_path.write_text(yaml.safe_dump(_mock_config.template), encoding="utf-8")
    individual_path = tmp_path / "individual.yaml"
    individual_path.write_text(yaml.safe_dump(_mock_config.individual), encoding="utf-8")

    Paths = namedtuple("Paths", ["template", "individual"])

    return _mock_config, Paths(template_path, individual_path)


@pytest.fixture()
def mock_api_keys(monkeypatch):
    """API キーをモック設定（全テスト共通）"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


@pytest.fixture
def no_api_keys(monkeypatch):
    """環境変数をクリア"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def disable_sample_save(monkeypatch):
    """全テストで AI 出力サンプル保存を無効化"""
    monkeypatch.delenv("SAVE_AI_OUTPUTS", raising=False)


@pytest.fixture
def mock_async_client(monkeypatch):
    """httpx.AsyncClientをモック"""
    # 1. レスポンスの準備
    mock_response = MagicMock()
    mock_response.text = "<html>...</html>"
    mock_response.raise_for_status = MagicMock()  # 必要なら追加

    # 2. クライアント（instance）の準備
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    # 3. コンテキストマネージャ（async with）としての振る舞いを設定
    # AsyncClient() が呼ばれた際に、この mock_client 自身が返るようにする
    mock_factory = MagicMock(return_value=mock_client)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(httpx, "AsyncClient", mock_factory)

    return mock_client


@pytest.fixture
def sample_url():
    return "https://sample.com/"


@pytest.fixture
def sample_llm_config():
    """共通のLLM設定"""
    return {
        "prompt": "テスト用プロンプト",
        "model": "deepseek-chat",
        "temperature": 0.3,
        "data": "テスト用データ",
        "prompt_key": "test_key",
    }


@pytest.fixture
def sample_prompt_data():
    """テスト用プロンプトとデータ"""
    return {"prompt": "テスト用プロンプト", "data": "テスト用データ"}


@pytest.fixture
def sample_token_stats():
    # ログ出力（:.4f や :.2f）でエラーにならないよう数値を設定
    mock_stats = MagicMock()
    mock_stats.total_fee = 0.0015
    mock_stats.execution_time = 1.23
    # LlmStatsが内部で要求する属性も念のため数値にしておく
    mock_stats.prompt_tokens = 100
    mock_stats.completion_tokens = 50
    return mock_stats


@pytest.fixture
def mock_openai_response():
    """OpenAI APIレスポンスのモック"""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"trail_condition_records": []}'
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.completion_tokens_details.reasoning_tokens = 0

    return mock_response


@pytest.fixture
def mock_gemini_response():
    """Gemini APIレスポンスのモック"""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.text = '{"trail_condition_records": []}'
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock(text="", thought=False)]
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.thoughts_token_count = 20
    mock_response.usage_metadata.candidates_token_count = 50
    mock_response.usage_metadata.total_token_count = 170

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

    return asyncio.WindowsProactorEventLoopPolicy() if os.name == "nt" else asyncio.DefaultEventLoopPolicy()
