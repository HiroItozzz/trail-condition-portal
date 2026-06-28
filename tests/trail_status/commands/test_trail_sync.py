from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from trail_status.management.commands.trail_sync import Command
from trail_status.models import DataSource
from trail_status.services.llm_client import DeepseekClient, GeminiClient, GptClient
from trail_status.services.prompt_utils import PromptFile
from trail_status.services.types import ResultSingle, SourceSchemaSingle

DATASOURCE_TEST_DATA_1 = {
    "id": 1,
    "name": "テスト機関",
    "prefecture_code": "",
    "prompt_key": "test.org",
    "url1": "http://test.org",
    "url2": "",
    "description": "テスト詳細説明",
    "content_hash": "dummy1",
}

DATASOURCE_TEST_DATA_2 = {
    "id": 2,
    "name": "テスト機関2",
    "prefecture_code": "",
    "data_format": "WEB",
    "prompt_key": "test2_org",
    "url1": "http://test-2.org",
    "url2": "",
    "description": "テスト詳細説明2",
    "content_hash": "dummy2",
}

DATASOURCE_TEST_DATA_BLOG = {
    "id": 3,
    "name": "テスト機関3",
    "prefecture_code": "",
    "data_format": "BLOG",
    "prompt_key": "test3_org",
    "url1": "http://test-3.org",
    "url2": "",
    "description": "テスト詳細説明3",
    "content_hash": "dummy3",
}

class SimpleSetup(SimpleTestCase):
    def setUp(self):
        self.command = Command()


class DbSetup(TestCase):
    def setUp(self):
        DataSource.objects.create(**DATASOURCE_TEST_DATA_1)
        DataSource.objects.create(**DATASOURCE_TEST_DATA_2)
        DataSource.objects.create(**DATASOURCE_TEST_DATA_BLOG)
        self.command = Command()


@patch("trail_status.management.commands.trail_sync.Command.print_summary")
@patch("trail_status.management.commands.trail_sync.Command.generate_summary")
@patch("trail_status.management.commands.trail_sync.Command.process_result")
@patch("trail_status.management.commands.trail_sync.AiPipeline")
@patch("trail_status.management.commands.trail_sync.Command.setup_data_source")
class TestHandle(SimpleSetup):
    def setUp(self):
        super().setUp()
        self.options = {"dry_run": False, "new_hash": False}
        self.mock_data_sources = [SourceSchemaSingle(id=1, name="dummy", url1="dummyurl", prompt_file=PromptFile())]
        self.ai_results = [ResultSingle(success=True, message="ok")]

        self.pipeline_results = list(zip(self.mock_data_sources, self.ai_results))

    def test_main(self, mock_setup, MockPipeline, mock_process, mock_generate, mock_print):
        """正常な処理"""
        mock_setup.return_value = self.mock_data_sources
        mock_pipeline = MockPipeline.return_value
        mock_pipeline.run = AsyncMock(return_value=self.pipeline_results)

        self.command.handle(**self.options)

        mock_setup.assert_called_once_with(None)
        mock_pipeline.run.assert_called_once()
        mock_process.assert_called_once_with(*self.pipeline_results[0], new_hash_mode=False)
        mock_generate.assert_called_once_with(self.pipeline_results)
        mock_print.assert_called_once()

    def test_main_dry_run(self, mock_setup, MockPipeline, mock_process, mock_generate, mock_print):
        """DBに保存しないドライランモードのテスト"""
        mock_setup.return_value = self.mock_data_sources
        mock_pipeline = MockPipeline.return_value
        mock_pipeline.run = AsyncMock(return_value=self.pipeline_results)

        # dry_runのフラグをオン
        self.options["dry_run"] = True
        self.command.handle(**self.options)

        # DB処理のメソッドをスキップ（呼び出しなし）
        mock_process.assert_not_called()
        # それ以外は通常処理
        mock_setup.assert_called_once_with(None)
        mock_pipeline.run.assert_called_once()
        mock_generate.assert_called_once_with(self.pipeline_results)
        mock_print.assert_called_once()


@patch("trail_status.management.commands.trail_sync.PromptFile")
class TestSetupDataSource(DbSetup):
    def test_setup_datasource(self, MockPromptFile):
        """情報源のDBからの通常取得"""
        MockPromptFile.load_merged_config = MagicMock(return_value=PromptFile())
        result = self.command.setup_data_source(source_id=None)

        result_1, result_2 = result

        assert len(result) == 2
        assert isinstance(result_1, SourceSchemaSingle)
        assert MockPromptFile.load_merged_config.call_count == len(result)

        assert result_1.id == DATASOURCE_TEST_DATA_1["id"]
        assert result_1.name == DATASOURCE_TEST_DATA_1["name"]
        assert result_1.url1 == DATASOURCE_TEST_DATA_1["url1"]
        assert result_1.content_hash == DATASOURCE_TEST_DATA_1["content_hash"]

        assert result_2.name == DATASOURCE_TEST_DATA_2["name"]

    def test_setup_datasource_source_id_set(self, MockPromptFile):
        """単一情報源の取得の処理（コマンドライン引数指定）"""
        MockPromptFile.load_merged_config = MagicMock(return_value=PromptFile())
        result = self.command.setup_data_source(source_id=1)

        result = result.pop()

        assert isinstance(result, SourceSchemaSingle)
        MockPromptFile.load_merged_config.assert_called_once()

        assert result.name == DATASOURCE_TEST_DATA_1["name"]
        assert result.url1 == DATASOURCE_TEST_DATA_1["url1"]
        assert result.content_hash == DATASOURCE_TEST_DATA_1["content_hash"]

    def test_setup_datasource_source_data_format_is_not_WEB(self, MockPromptFile):
        """単一情報源のdata_format != 'WEB'時の挙動"""
        MockPromptFile.load_merged_config = MagicMock(return_value=PromptFile())
        result = self.command.setup_data_source(source_id=3)

        assert result is None
        MockPromptFile.load_merged_config.assert_not_called()

    def test_setup_datasource_source_data_not_exists(self, MockPromptFile):
        """単一情報源の指定IDが存在しなかったときの挙動"""
        MockPromptFile.load_merged_config = MagicMock(return_value=PromptFile())
        result = self.command.setup_data_source(source_id=1000)

        assert result is None
        MockPromptFile.load_merged_config.assert_not_called()


@patch("trail_status.management.commands.trail_sync.SlackNotifier")
@patch("trail_status.management.commands.trail_sync.DbWriter")
class TestProcessResult(SimpleSetup):
    def setUp(self):
        super().setUp()
        self.db_result_1 = {"name": "source_1", "updated": 1, "created": 1, "count": 2, "cost": 0.11111}
        self.source_schema = SourceSchemaSingle(id=1, name="dummy", url1="http://dummy.com/", prompt_file=PromptFile())
        self.result_by_source = ResultSingle(success=True, message="success", content_changed=True)

    def test_success_cases(self, MockWriter, MockNotifier):
        """サイト変更あり・パイプライン正常終了時の挙動"""
        mock_writer, mock_notifier = MockWriter.return_value, MockNotifier.return_value
        mock_writer.save_to_source = MagicMock()
        mock_writer.persist_condition_and_usage = MagicMock(return_value=self.db_result_1)
        mock_notifier.send_update_notification = MagicMock()

        self.command.process_result(self.source_schema, self.result_by_source, new_hash_mode=None)

        # 保存呼び出し+スラック通知
        mock_writer.save_to_source.assert_called_once()
        mock_writer.persist_condition_and_usage.assert_called_once()
        mock_notifier.send_update_notification.assert_called_once()

    def test_content_not_changed(self, MockWriter, MockNotifier):
        """サイト変更なし時の挙動"""
        self.result_by_source.content_changed = False

        mock_writer, mock_notifier = MockWriter.return_value, MockNotifier.return_value
        mock_writer.save_to_source = MagicMock()
        mock_writer.persist_condition_and_usage = MagicMock()
        mock_notifier.send_update_notification = MagicMock()
        mock_notifier.send_error_notification = MagicMock()

        self.command.process_result(self.source_schema, self.result_by_source, new_hash_mode=None)

        mock_writer.save_to_source.assert_called_once()
        # 登山道状態更新なし+スラック通知なし
        mock_writer.persist_condition_and_usage.assert_not_called()
        mock_notifier.send_update_notification.assert_not_called()
        mock_notifier.send_error_notification.assert_not_called()

    def test_pipeline_failure(self, MockWriter, MockNotifier):
        """パイプライン処理失敗時の挙動"""
        self.result_by_source.success = False

        mock_writer, mock_notifier = MockWriter.return_value, MockNotifier.return_value
        mock_writer.save_to_source = MagicMock()
        mock_writer.persist_condition_and_usage = MagicMock()
        mock_notifier.send_update_notification = MagicMock()
        mock_notifier.send_error_notification = MagicMock()

        self.command.process_result(self.source_schema, self.result_by_source, new_hash_mode=None)

        # エラー通知
        mock_notifier.send_error_notification.assert_called_once()
        # 情報源テープル更新なし・登山道状態更新なし
        mock_writer.save_to_source.assert_not_called()
        mock_writer.persist_condition_and_usage.assert_not_called()
        mock_notifier.send_update_notification.assert_not_called()


@pytest.mark.parametrize(
    "model,expected_client",
    [
        ("deepseek-reasoner", DeepseekClient),
        ("gemini-3-flash-preview", GeminiClient),
        ("gpt-5-mini", GptClient),
    ],
)
def test_client_factory(model, expected_client):
    """AIクライアントのファクトリーメソッドのテスト"""
    mock_config = MagicMock()
    mock_config.model = model

    result = Command().default_client_factory(mock_config)

    assert isinstance(result, expected_client)


def test_parser(capsys):
    """引数定義のテスト"""
    expected_args = ["--source", "--model", "--dry-run", "--new-hash"]

    with pytest.raises(SystemExit) as exc_info:
        call_command("trail_sync", "--help")

    out, _ = capsys.readouterr()

    assert exc_info.value.code == 0
    assert all(a in out for a in expected_args)
