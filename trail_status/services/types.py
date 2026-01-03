from typing import Any

from .llm_stats import TokenStats

SourceDataSingle = dict[str, Any]

UpdatedDataSingle = dict[str, bool | int | list[dict] | TokenStats]
UpdatedDataList = list[tuple[SourceDataSingle, UpdatedDataSingle]]
