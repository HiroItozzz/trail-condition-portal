# レコード照合アルゴリズム

```mermaid
flowchart TB
    INPUT["AI出力レコード群"] --> MATRIX["全ペアの類似度計算<br>SudachiPy トークン化 → RapidFuzz スコア"]
    EXISTING["既存DBレコード群"] --> MATRIX

    MATRIX --> THRESHOLD{"スコア ≥ 0.7 ?"}
    THRESHOLD -- Yes --> GREEDY["スコア降順で貪欲割り当て"]
    THRESHOLD -- No --> CREATE["新規作成"]

    GREEDY --> CHANGED{"内容に変更あり？"}
    CHANGED -- Yes --> UPDATE["既存レコード更新"]
    CHANGED -- No --> NOOP([スキップ])
```

## フィールド重み

| フィールド | 重み | 備考 |
|:---:|:---:|:---|
| mountain | 0.2 | 名詞のみでトークン化 |
| trail | 0.3 | 全品詞 |
| title | 0.1 | 全品詞 |
| desc | 0.4 | 先頭200文字で比較 |

desc欠損時は trail:0.4 / title:0.4 に自動切替。
