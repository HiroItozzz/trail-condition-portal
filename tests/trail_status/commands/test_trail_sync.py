import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from trail_status.management.commands.trail_sync import Command
from trail_status.models import DataSource
from trail_status.services.prompt_utils import PromptFile
from trail_status.services.types import ResultSingle, SourceSchemaSingle

DATASOURCE_TEST_DATA_1 = {
    "name": "テスト機関",
    "prefecture_code": "",
    "prompt_key": "test.org",
    "url1": "http://test.org",
    "url2": "",
    "description": "テスト詳細説明",
    "content_hash": "dummy1",
}

DATASOURCE_TEST_DATA_2 = {
    "name": "テスト機関2",
    "prefecture_code": "",
    "prompt_key": "test2_org",
    "url1": "http://test-2.org",
    "url2": "",
    "description": "テスト詳細説明2",
    "content_hash": "dummy2",
}

EXPECTED_1 = ResultSingle(
    success=True,
    message="取得成功",
    new_hash="dummy_hash",
    scraped_length=1234,
    content_changed=True,
)


class TestBatch(TestCase):
    def setUp(self):
        DataSource.objects.create(**DATASOURCE_TEST_DATA_1)
        DataSource.objects.create(**DATASOURCE_TEST_DATA_2)
        self.command = Command()

    @patch("trail_status.management.commands.trail_sync.PromptFile")
    def test_setup_datasource(self, MockPromptFile):

        MockPromptFile.load_merged_config = MagicMock(return_value=PromptFile())
        result = self.command.setup_data_source(source_id=None)

        result_1, result_2 = result

        assert len(result) == 2 
        assert isinstance(result_1, SourceSchemaSingle)
        assert MockPromptFile.load_merged_config.call_count == len(result)
        
        assert result_1.name == DATASOURCE_TEST_DATA_1["name"]
        assert result_1.url1 == DATASOURCE_TEST_DATA_1["url1"]
        assert result_1.content_hash == DATASOURCE_TEST_DATA_1["content_hash"]

        assert result_2.name == DATASOURCE_TEST_DATA_2["name"]


"""    def test_trail_sync(self,MockPipeline):  
        mock_run = AsyncMock(return_value=)
        mock_instance = MockPipeline.return_value
        mock_instance.run.return_value = AsyncMock
"""
