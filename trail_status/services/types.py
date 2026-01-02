from .llm_stats import TokenStats

SourceDataSingle = dict[str, int | str]

UpdatedDataSingle = dict[str, bool | int | list[dict] | TokenStats]
UpdatedDataList = list[tuple[SourceDataSingle, UpdatedDataSingle]]
