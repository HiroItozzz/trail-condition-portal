import os

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)
django.setup()


import asyncio
from pathlib import Path

from trail_status.services.llm_client import DeepseekClient, LlmConfig, get_prompts_dir, get_sample_dir

PROMPT_DIR = get_prompts_dir() / "001_okutama_vc.yaml"
SAMPLE_DIR = get_sample_dir() / "sample_okutama.txt"
D_MODEL = "deepseek-reasoner"
G_MODEL = "gemini-3-flash-preview"

prompt = LlmConfig.load_prompt("001_okutama_vc.yaml")
data = SAMPLE_DIR.read_text(encoding="utf-8")

if __name__ == "__main__":
    d_config = LlmConfig(site_prompt=prompt, model=D_MODEL, data=data)
    g_config = LlmConfig(site_prompt=prompt, model=G_MODEL, data=data)

    results = [asyncio.run(DeepseekClient(d_config).generate())]
    # results = [asyncio.run(GeminiClient(g_config).generate())]

    """    async def compare():
            results = await asyncio.gather(
                DeepseekClient(d_config).generate(), GeminiClient(g_config).generate(), return_exceptions=True
            )

            return results

        results = asyncio.run(compare())
    """
    from pprint import pprint

    for idx, (output, stats) in enumerate(results, 1):
        print(f"==================結果{idx}=======================")
        print()
        print("=======AIによる出力=======")
        pprint(output)
        print("=======AIによるコスト分析=======")
        pprint(stats)
        print(f"思考料金： ${stats.thoughts_fee}")
        print(f"トータル料金： ${stats.total_fee}")
