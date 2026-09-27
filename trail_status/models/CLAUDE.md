# models/

- `StatusType`（`condition.py`）と `AreaName`（`mountain.py`）は DB の選択肢であり、同時に AI スキーマ（`services/types.py`）の選択肢でもある。`AreaName` のラベルは AI へのプロンプト文にも埋め込まれる。値やラベルを変えると AI の出力も変わる。
- `PromptBackup` は管理画面に登録されているだけで、書き込む処理はない。DB のバックアップは `management/commands/backup_db.py`。
