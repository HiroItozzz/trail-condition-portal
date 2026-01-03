from typing import Any

from .llm_client import LlmConfig
from .llm_stats import LlmStats
from .schema import TrailConditionSchemaList

ModelDataSingle = dict[str, Any]

UpdatedDataSingle = dict[str, bool | int | str | TrailConditionSchemaList | LlmStats | LlmConfig]
UpdatedDataList = list[tuple[ModelDataSingle, UpdatedDataSingle]]
