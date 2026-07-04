import asyncio
import logging
import os
from pathlib import Path
from pprint import pprint
from typing import override

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.production",
)
django.setup()

from django.conf import settings

from trail_status.models import DataSource
from trail_status.services.llm_client import GeminiClient, LlmConfig
from trail_status.services.llm_stats import TokenStats
from trail_status.services.prompt_utils import PromptFile, get_prompt_dir
from trail_status.services.types import LlmModel

logger = logging.getLogger(__name__)


SOURCE_ID = 6
MODEL = LlmModel.GEMINI_3_1_FLASH_LITE
data_path: Path = list((settings.BASE_DIR / "outputs/fetched_content").glob(f"{SOURCE_ID:03}*")).pop()


class SampleGeminiClient(GeminiClient):
    @override
    def _create_token_stats(self, raw_response):
        for part in raw_response.candidates[0].content.parts:
            if not part.text:
                continue
            elif part.thought:
                logger.debug("## **Thoughts summary:**")
                logger.debug(part.text)
            else:
                logger.debug("## **Answer:**")
                logger.debug(part.text)

        # Noneチェック
        if metadata := raw_response.usage_metadata:
            prompt_tokens = metadata.prompt_token_count
            thoughts_tokens = getattr(metadata, "thoughts_token_count", 0) or 0
            output_tokens = metadata.candidates_token_count

            tool_tokens = metadata.tool_use_prompt_token_count
            tool_details = metadata.tool_use_prompt_tokens_details
            print("─" * 6, "ツール使用トークン詳細", "─" * 25)
            print(f"{tool_tokens=}")
            print(f"{tool_details=}")
            print(f"{metadata=}")
            print(f"{raw_response=}")
            print(f"{raw_response.function_calls=}")
            print("─" * 50)

        else:
            logger.warning("Gemini API response did not include usage metadata.")
            prompt_tokens = 0
            thoughts_tokens = 0
            output_tokens = 0

        stats = TokenStats(
            prompt_tokens,
            thoughts_tokens,
            output_tokens,
            len(self.prompt),
            len(raw_response.text),
            self.model,
        )
        return stats


if __name__ == "__main__":
    data = data_path.read_text(encoding="utf-8")
    data_source = DataSource.objects.get(pk=SOURCE_ID)
    prompt_file = PromptFile.load_merged_config(data_source.prompt_filename, url=data_source.url1)
    config = LlmConfig.from_file(prompt_file=prompt_file, data=data, model=MODEL)

    results = [asyncio.run(SampleGeminiClient(config).generate())]

    for idx, (output, stats) in enumerate(results, 1):
        print(f"─────── 結果{idx} ───────────────────────────")
        print("─────── AIによる出力 ───────────────────────────")
        pprint(output)
        print("─────── AIによるコスト分析 ────────────────────────────")
        pprint(stats)
        print(f"思考料金： ${stats.thoughts_fee}")
        print(f"トータル料金： ${stats.total_fee}")
