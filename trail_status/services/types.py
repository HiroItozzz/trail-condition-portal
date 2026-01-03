from typing import Any

from .llm_stats import LlmStats
from .schema import TrailConditionSchemaList

ModelDataSingle = dict[str, Any]

UpdatedDataSingle = dict[str, bool | int | TrailConditionSchemaList | LlmStats]
UpdatedDataList = list[tuple[ModelDataSingle, UpdatedDataSingle]]
