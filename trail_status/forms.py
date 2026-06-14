import logging

import yaml
from django import forms
from django.db import models

from .services import utils

logger = logging.getLogger(__name__)
PROMPT_DIR = utils.get_prompts_dir()


# fmt: off
class LlmModel(models.TextChoices):
    GEMINI_2_5_FLASH        = "gemini-2.5-flash",        "Gemini 2.5 Flash"
    GEMINI_2_5_PRO          = "gemini-2.5-pro",          "Gemini 2.5 Pro"
    GEMINI_3_FLASH_PREVIEW  = "gemini-3-flash-preview",  "Gemini 3 Flash Preview"
    GEMINI_3_1_FLASH_LITE   = "gemini-3.1-flash-lite",   "Gemini 3.1 Flash Lite"
    GEMINI_3_5_FLASH        = "gemini-3.5-flash",        "Gemini 3.5 Flash"
    GEMINI_FLASH_LATEST     = "gemini-flash-latest",     "Gemini Flash Latest"
    DEEPSEEK_CHAT           = "deepseek-chat",           "DeepSeek Chat"
    DEEPSEEK_REASONER       = "deepseek-reasoner",       "DeepSeek Reasoner"
    GPT_5_MINI              = "gpt-5-mini",              "GPT-5 Mini"
    GPT_5_NANO              = "gpt-5-nano",              "GPT-5 Nano"
# fmt: on


class PromptForm(forms.Form):
    title = forms.CharField(label="対象の情報源の名前", max_length=200, disabled=True)
    filename = forms.CharField(label="プロンプトのファイル名", max_length=60, disabled=True)
    prompt = forms.CharField(label="個別プロンプト", widget=forms.Textarea)
    model = forms.ChoiceField(label="使用するモデル", choices=LlmModel.choices, initial=LlmModel.GEMINI_3_FLASH_PREVIEW)
    temperature = forms.FloatField(label="温度(0〜2.0)", min_value=0, max_value=2.0, step_size=0.1)
    thinking_budget = forms.IntegerField(label="思考予算(-1〜30000)", min_value=-1, max_value=30000)
    use_template = forms.BooleanField(label="テンプレートファイルの使用", initial=True, required=False)

    def __init__(self, data_source, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            if data_source:
                filename = utils.get_prompt_filename_from_data(data_source)
                prompt_path = PROMPT_DIR / filename
                prompt_data = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
                model_config = prompt_data.get("config", {}) or {}

                self.fields["title"].initial = data_source.name
                self.fields["filename"].initial = filename
                self.fields["prompt"].initial = prompt_data.get("prompt") or ""
                self.fields["model"].initial = model_config.get("model") or ""
                self.fields["temperature"].initial = model_config.get("temperature") or 0.6
                self.fields["thinking_budget"].initial = model_config.get("thinking_budget") or ""

        except Exception:
            logger.exception()
