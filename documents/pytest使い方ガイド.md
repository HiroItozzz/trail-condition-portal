# pytest 使い方ガイド

このプロジェクトでのpytestの使い方を解説します。

## 前提条件

### 環境準備（初回のみ）

```bash
# 開発用依存関係をインストール
uv sync --dev
```

これで以下がインストールされます：
- pytest
- pytest-asyncio (非同期テスト用)
- pytest-django (Django統合)

## 基本的なテスト実行

### 全テスト実行

```bash
# 全テスト実行
uv run pytest

# 詳細な出力（推奨）
uv run pytest -v

# print文も表示
uv run pytest -vs
```

### 特定のテストだけ実行

```bash
# ファイル単位
uv run pytest trail_status/tests/test_schema_validation.py

# 関数単位
uv run pytest trail_status/tests/test_schema_validation.py::test_valid_schema_validation

# パターンマッチ（-k）
uv run pytest -k "schema"                    # "schema"を含むテスト
uv run pytest -k "llm and not gemini"        # "llm"を含み、"gemini"を含まない
```

## 便利なオプション

### デバッグ・開発用

```bash
# 失敗したテストで即座に停止
uv run pytest -x

# 最初のN個の失敗で停止
uv run pytest --maxfail=3

# 前回失敗したテストのみ再実行
uv run pytest --lf

# 前回失敗したテストを優先的に実行
uv run pytest --ff

# 詳細なトレースバックを表示
uv run pytest --tb=long

# 各テストの実行時間を表示
uv run pytest --durations=10

# 標準出力を表示（print文が見える）
uv run pytest -s
```

### カバレッジ測定

```bash
# カバレッジ測定（pytest-covが必要）
uv run pytest --cov=trail_status

# HTML形式のレポート生成
uv run pytest --cov=trail_status --cov-report=html

# 特定のモジュールのカバレッジ
uv run pytest --cov=trail_status.services --cov-report=term-missing
```

## Django特有の機能

### データベース関連

```bash
# データベースを再利用（高速化）
uv run pytest --reuse-db

# データベースを再作成
uv run pytest --create-db

# データベース作成をスキップ（非DB テスト用）
uv run pytest --no-migrations
```

### ログ出力

```bash
# ログレベルを指定して実行
uv run pytest -v --log-cli-level=DEBUG

# ログをファイルに保存
uv run pytest --log-file=test.log --log-file-level=DEBUG
```

## よく使うコマンド例

### スキーマテストだけ実行

```bash
uv run pytest trail_status/tests/test_schema_validation.py -v
```

### LLMクライアントのテスト（詳細表示）

```bash
uv run pytest trail_status/tests/test_llm_clients.py -vs
```

### 全テストを詳細表示で実行

```bash
uv run pytest -vv
```

### 非同期テストだけ実行

```bash
uv run pytest -m asyncio
```

### 特定のキーワードを含むテストを実行

```bash
# "config"を含むテストのみ
uv run pytest -k config -v

# "llm"を含むが"gemini"を含まないテスト
uv run pytest -k "llm and not gemini" -v
```

## テスト結果の見方

### 成功の場合

```
trail_status/tests/test_schema_validation.py::test_valid_schema_validation PASSED [100%]
```

- `PASSED`: テスト成功
- `[100%]`: 進捗状況

### 失敗の場合

```
trail_status/tests/test_llm_clients.py::test_deepseek_generate_success FAILED
```

失敗理由が詳細に表示されます。

### スキップの場合

```
trail_status/tests/test_integration.py::test_full_pipeline SKIPPED
```

`@pytest.mark.skip` でマークされたテストです。

## プロジェクト固有の設定

### pyproject.toml の設定

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
pythonpath = ["."]
testpaths = ["trail_status/tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

- **DJANGO_SETTINGS_MODULE**: Django設定が自動読み込み
- **asyncio_mode = "auto"**: `@pytest.mark.asyncio` が自動適用
- **testpaths**: テストディレクトリの指定

## トラブルシューティング

### インポートエラーが出る場合

```bash
# Pythonパスを確認
uv run python -c "import sys; print(sys.path)"

# プロジェクトルートから実行しているか確認
pwd
```

### データベースエラーが出る場合

```bash
# データベースを再作成
uv run pytest --create-db
```

### 非同期テストが動かない場合

```bash
# pytest-asyncioがインストールされているか確認
uv pip list | grep pytest-asyncio

# 明示的にasyncioモードを指定
uv run pytest --asyncio-mode=auto
```

## CI/CD での実行

GitHub Actionsなどで実行する場合：

```bash
# 出力をJUnit XML形式で保存
uv run pytest --junitxml=test-results.xml

# カバレッジと組み合わせ
uv run pytest --cov=trail_status --cov-report=xml --junitxml=test-results.xml
```

## テストの書き方

### 基本的なテスト

```python
def test_example():
    """テストの説明"""
    assert 1 + 1 == 2
```

### 非同期テスト

```python
@pytest.mark.asyncio
async def test_async_function():
    """非同期関数のテスト"""
    result = await some_async_function()
    assert result is not None
```

### フィクスチャを使う

```python
def test_with_fixture(mock_api_keys):
    """フィクスチャを使ったテスト"""
    config = LlmConfig(model="deepseek-chat", data="test")
    assert config.api_key == "test-deepseek-key"
```

## まとめ

- **開発時**: `uv run pytest -v` で詳細表示
- **デバッグ時**: `uv run pytest -vs -x` で失敗時に即停止
- **特定テスト**: `uv run pytest -k "キーワード"`
- **カバレッジ**: `uv run pytest --cov=trail_status`

pytestの詳細は[公式ドキュメント](https://docs.pytest.org/)を参照してください。
