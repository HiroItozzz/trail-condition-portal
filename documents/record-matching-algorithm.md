# レコード同定アルゴリズム

## 概要

登山道状況データのレコード同定は、AIが抽出した新規データと既存DBレコードを照合し、同一の登山道状況かを判定する重要な処理です。

AIの出力には「山名」「登山道名」などの揺らぎ（表記ゆれ）があるため、単純な完全一致では同定が困難です。本実装では**RapidFuzz**ライブラリを用いた3段階のハイブリッドアルゴリズムで高精度な同定を実現しています。

## 問題の背景

### AIの揺らぎの例

| 1回目 | 2回目 | 判定 |
|-------|-------|------|
| 雲取山 | 雲取山登山口 | 同じ通行止め |
| 鴨沢ルート | 鴨沢登山口ルート | 同じ通行止め |
| 三頭山～御前山 | 御前山～三頭山 | 同じ通行止め |
| 大岳山 | 高尾山 | 別の通行止め |

Temperature=0.0 でも完全に揺らぎをなくすことはできません。

### なぜ同定が必要か

1. **データ鮮度の管理**: 「いつ取得されたデータか」「どのくらい前の情報か」をユーザーに提示
2. **重複排除**: 同じ通行止めが複数レコードとして残るのを防ぐ
3. **履歴追跡**: 同一の通行止めがいつから継続しているかを把握

## 3段階ハイブリッドアルゴリズム

### ステップ1: 候補の絞り込み

```python
candidates = TrailCondition.objects.filter(
    source=self.source_record,      # 同じ情報源
    disabled=False,                  # 無効化されていない
    resolved_at__isnull=True,       # 解消済みでない
)
```

**設計判断**:
- `area`（山域）でフィルタ**しない** → 山域にも揺らぎがあるため
- `source`のみで絞る → 各データソースは独立（最大50件程度）
- `resolved_at__isnull=True` → 解消済みの通行止めと新規を区別

### ステップ2: 完全一致チェック（高速パス）

```python
normalized_m = normalize_text(new_data.mountain_name_raw)
normalized_t = normalize_text(new_data.trail_name)

for candidate in candidates:
    if (normalize_text(candidate.mountain_name_raw) == normalized_m
        and normalize_text(candidate.trail_name) == normalized_t):
        existing_record = candidate
        break
```

**normalize_text()の処理**:
- Unicode正規化（NFKC）
- 前後の空白削除
- 全角スペース・半角スペース削除

**想定カバー率**: 約90% のケースがここで同定完了

### ステップ3: 類似度計算（フォールバック）

完全一致しなかった場合、RapidFuzzで複数フィールドの類似度を計算します。

## 類似度スコアリング詳細

### 使用フィールドと重み

| フィールド | 重み | アルゴリズム | 理由 |
|-----------|------|-------------|------|
| mountain_name_raw | 0.30 | `partial_ratio` | 山名は最重要識別子、部分一致を許容 |
| trail_name | 0.30 | `token_sort_ratio` | 登山道名も最重要、順序無視で比較 |
| title | 0.25 | `partial_ratio` | 状況要約として有用 |
| description | 0.15 | `token_set_ratio` | 長文で揺れが大きいため控えめ |

**descriptionがない場合**: 3フィールドに重み再配分（0.35, 0.35, 0.30）

### RapidFuzzアルゴリズムの選択理由

#### `partial_ratio` (部分一致)
- 「雲取山」と「雲取山登山口」 → 100点
- 短い方が長い方に含まれていればマッチ

#### `token_sort_ratio` (トークン順序無視)
- 「三頭山～御前山」と「御前山～三頭山」 → 100点
- 単語を分割してソート後に比較

#### `token_set_ratio` (トークンセット比較)
- 共通トークンの割合を計算
- 長文の部分的な一致を検出

### ボーナススコア

```python
# ボーナス1: statusが一致（+0.1）
if existing.status == new_data.status:
    base_score = min(1.0, base_score + 0.1)

# ボーナス2: 報告日が近い（±14日以内で+0.05）
if new_data.reported_at and existing.created_at:
    days_diff = abs((existing.created_at.date() - new_data.reported_at).days)
    if days_diff <= 14:
        base_score = min(1.0, base_score + 0.05)
```

### 判定閾値

```python
if best_score >= 0.7:
    # 同定成功 → 既存レコードを更新
else:
    # 類似度不足 → 新規レコード作成
```

**閾値 0.7 の根拠**:
- 0.8以上: 厳しすぎて揺らぎを吸収できない
- 0.6以下: 緩すぎて誤同定のリスク
- **0.7**: バランスが良く、実用的

## 設定可能なパラメータ

**全てのパラメータは `DbWriter` クラスの定数として定義されています（`db_writer.py` L37-58）**

### 1. 類似度閾値 (Similarity Threshold)

**定数名**: `SIMILARITY_THRESHOLD`
**デフォルト値**: `0.7`

```python
class DbWriter:
    SIMILARITY_THRESHOLD = 0.7  # ← ここを変更
```

**推奨値**:
- `0.8`: 厳格モード（精度重視、新規作成が増える）
- `0.7`: バランスモード（推奨）
- `0.6`: 緩和モード（重複回避重視、誤同定リスク増）

### 2. フィールド重み

#### 4フィールド使用時（description有り）

```python
FIELD_WEIGHT_MOUNTAIN = 0.30  # 山名
FIELD_WEIGHT_TRAIL = 0.30     # 登山道名
FIELD_WEIGHT_TITLE = 0.25     # タイトル
FIELD_WEIGHT_DESC = 0.15      # 詳細説明
```

#### 3フィールド使用時（description無し）

```python
FIELD_WEIGHT_MOUNTAIN_NO_DESC = 0.35
FIELD_WEIGHT_TRAIL_NO_DESC = 0.35
FIELD_WEIGHT_TITLE_NO_DESC = 0.30
```

**調整例**:
- 山名を最重要視: `0.40, 0.30, 0.20, 0.10`
- タイトル重視: `0.25, 0.25, 0.35, 0.15`

**注意**: 4つの重みの合計は必ず `1.0` になるようにすること

### 3. ボーナススコア

```python
BONUS_STATUS_MATCH = 0.1      # status一致時のボーナス
BONUS_DATE_PROXIMITY = 0.05   # 日付が近い時のボーナス
```

**調整可能**:
- `BONUS_STATUS_MATCH`: `0.05 ~ 0.15`
- `BONUS_DATE_PROXIMITY`: `0.03 ~ 0.10`

### 4. 日付近接判定の範囲

```python
DATE_PROXIMITY_DAYS = 14  # 報告日の±14日以内
```

**調整可能**: `7 ~ 30日`
- 短い（7日）: 厳格な日付一致を要求
- 長い（30日）: より広い範囲で同定

### 5. description の使用文字数

```python
DESC_COMPARE_LENGTH = 100  # 最初の100文字
```

**調整可能**: `50 ~ 200文字`
- 短い（50文字）: 高速、精度やや低
- 長い（200文字）: 遅い、精度やや高

## パフォーマンス特性

### 計算量

- **ステップ1**: O(1) - インデックス使用
- **ステップ2**: O(N) - N = 候補数（最大50件程度）
- **ステップ3**: O(N × M) - M = フィールド数（4）

**実測値**:
- 完全一致: ~1ms
- 類似度計算（50レコード）: ~50ms

### メモリ使用量

- 候補レコード: 50件 × ~1KB = 50KB
- 一時スコアリスト: 50件 × 16B = 800B
- **合計**: 約51KB（無視できるレベル）

## ログ出力

### 同定成功時

```
INFO 完全一致同定: 123 - 雲取山/鴨沢ルート
INFO 類似度同定: 456 - スコア 0.85 - 御岳山/ロックガーデン
```

### 同定失敗時

```
INFO 類似度不足: 最高スコア 0.55 - 新規作成 - 高尾山/1号路
```

### 運用での活用

- 類似度スコアを見て閾値調整の判断材料にする
- 0.65-0.75 のグレーゾーンが多い場合は閾値調整を検討
- 誤同定が発生した場合はログからスコアを確認

## 将来の改善案

### フェーズ1: 現状（実装済み）
- ✅ RapidFuzz 3段階アルゴリズム
- ✅ 閾値 0.7

### フェーズ2: 運用フィードバック
- 同定失敗ケースの収集
- 閾値の微調整（0.7 → 0.72など）
- フィールド重みの調整

### フェーズ3: AI補助（将来）
- スコア 0.6-0.7 の「微妙なケース」だけAIに確認
- コスト最小化 + 精度向上
- バッチ処理で効率化

### フェーズ4: 機械学習（アイデア）
- 過去の同定結果から学習
- 最適な重みを自動調整
- 情報源ごとに特化したモデル

## トラブルシューティング

### 問題: 同じ通行止めが重複して作成される

**原因**: 閾値が高すぎる

**解決策**:
1. ログで類似度スコアを確認
2. 閾値を下げる（0.7 → 0.65）
3. フィールド重みを調整

### 問題: 別の通行止めが誤って同定される

**原因**: 閾値が低すぎる

**解決策**:
1. 閾値を上げる（0.7 → 0.75）
2. 山名の重みを増やす（0.30 → 0.40）

### 問題: パフォーマンスが遅い

**原因**: 候補レコードが多すぎる

**解決策**:
1. `resolved_at` でさらに絞り込み
2. description の文字数を減らす（100 → 50）
3. 古いレコードを定期削除

## 参照

- **実装**: `trail_status/services/db_writer.py`
- **RapidFuzz**: https://github.com/maxbachmann/RapidFuzz
- **類似度アルゴリズム**: Levenshtein距離ベース
