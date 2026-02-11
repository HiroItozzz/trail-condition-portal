# refactor: models import の一元化レポート

## 概要

`trail_status/models/` 配下の各サブモジュールから個別にインポートしていた箇所を、
`models/__init__.py` で re-export する形に統一。
全ファイルのインポートを `from .models import ...` / `from trail_status.models import ...` の1行に集約した。

## 背景

- `views.py` が `from .models.condition import AreaName, DataSource` のように、`condition.py` 経由で他モジュールの名前を暗黙的に取得していた（たまたま動いているパターン）
- `admin.py` は6行にわたって5つのサブモジュールから個別インポートしていた
- どのクラスがどのサブモジュールにあるか利用側が知る必要があり、可読性が低かった

## 変更ファイル一覧（13ファイル）

### 新規作成

| ファイル | 内容 |
|---|---|
| `trail_status/models/__init__.py` | 全モデル・Enum を re-export、`__all__` 定義 |

### 変更

| ファイル | Before | After |
|---|---|---|
| `trail_status/admin.py` | 6行（5サブモジュールから個別import） | 1行 `from .models import ...` |
| `trail_status/views.py` | `from .models.condition import AreaName, DataSource, ...`（暗黙re-export依存） | `from .models import ...` |
| `trail_status/signals.py` | 2行（condition, mountain） | 1行 `from .models import ...` |
| `trail_status/services/db_writer.py` | 3行（condition, llm_usage, source） | 1行 `from ..models import ...` |
| `trail_status/services/schema.py` | 2行（condition, mountain） | 1行 `from ..models import ...` |
| `api/serializers.py` | 2行（condition, source） | 1行 `from trail_status.models import ...` |
| `api/views.py` | 2行（condition, source） | 1行 `from trail_status.models import ...` |
| `trail_status/tests/sample_schema.py` | `from trail_status.models.condition import StatusType` | `from trail_status.models import StatusType` |
| `trail_status/management/commands/blog_sync.py` | 2行（feed, source） | 1行 `from trail_status.models import ...` |
| `trail_status/management/commands/test_yamareco.py` | 2行（condition, mountain） | 1行 `from trail_status.models import ...` |
| `trail_status/management/commands/test_matching.py` | `from trail_status.models.source import DataSource` | `from trail_status.models import DataSource` |
| `trail_status/management/commands/trail_sync.py` | `from trail_status.models.source import DataSource` | `from trail_status.models import DataSource` |

## `models/__init__.py` の公開API

```python
from .condition import StatusType, TrailCondition
from .feed import BlogFeed
from .llm_usage import LlmUsage
from .mountain import AreaName, MountainAlias, MountainGroup
from .prompt_backup import PromptBackup
from .source import DataSource, OrganizationType
```

## 備考

- `services/__init__.py` は今回対象外。利用箇所が `management/commands/` と `tests/` に分散しており、必要なクラスがファイルごとに異なるため、明示的なインポートの方が可読性が高いと判断
- 各サブモジュール内部のインポート（例: `condition.py` → `from .mountain import AreaName`）は変更なし
