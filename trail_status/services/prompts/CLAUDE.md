# prompts/

情報源ごとの LLM プロンプト（YAML）。

## 変更しない
- プロンプト本文と `config`（model / temperature / thinking_budget / use_template）は、オーナーの指示がない限り変更しない。変えると本番バッチの AI 出力が揺れ、既存レコードとの照合がずれて更新件数が増える。バッチの問題はオーナーが通知を見て対応する。
- `template.yaml` は全情報源のプロンプトの先頭に付くため、影響が最も大きい。
- ファイル名を変えない。

## 仕組み
- ファイル名は `{DataSource.id:03d}_{prompt_key}.yaml`（`DataSource.prompt_filename`）。
- `PromptFile.load_merged_config`（`../prompt_utils.py`）が `template.yaml` の本文に個別ファイルの本文をつなげ、`config` は個別ファイルに値があればそちらを使う。個別ファイルが `use_template: false` なら個別ファイルだけを使う。
- `template.yaml` の本文は `str.format` で `{scheme}` と `{netloc}` を置き換える。それ以外の波括弧は `{{` `}}` と書く。
- 新しい情報源は管理画面で登録する。バッチが初めて読み込むときにファイルがなければ `example.yaml` からコピーされるので、手で作らない。
- 組み立て後のプロンプトは `uv run python manage.py show_prompt <情報源ID>` で確認できる。
- `sample_tanzawa_vc.yaml` はコードから参照されていない。
