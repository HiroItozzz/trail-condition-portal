## 各SNSのOGのフォーマット

### 1. YAMAP記事のフォーマット
- og:site_name
  - YAMAP / ヤマップ
- og:title
  - 記事タイトル + 「｜YAMAP / ヤマップ」  
- og:description
  - 記事本文の冒頭120文字程度
- og:image
- og:url
- og:type

**問題点**
- 山行日がない
  - 検索時のメタデータに含まれていれば取得
  - descriptionに山行日を追加する…

### 2. ヤマレコ記事のフォーマット
- og:site_name
  - ヤマレコ
- og:title
  - 「山行記録: 」 {記事タイトル}
  - content="山行記録: 最短ルートで鷹ノ巣山ピストン"
- og:type
  - sport
- og:description
  - 山行日、エリアタグ、アクティビティタグ、 / {username}の山行記録
  - content="2025年12月16日(日帰り) 奥多摩・高尾, ハイキング / keidenの山行記録 "
- og:image

**問題点**
- 本文の内容が含まれていない
- 山行日がdescriptionに含まれている
  - 検索時のメタデータに含まれていれば取得
  - descriptionに山行日を追加する

### 3. 統一フォーマット