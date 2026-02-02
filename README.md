# Trail Condition Portal

## 概要

地方自治体、省庁等の公式サイトに散在する登山道の危険情報を自動収集し、一元的に閲覧できるサービスです。

**解決する課題**
- 登山道の危険情報は複数の公的機関サイトに分散している
- 各サイトの形式がバラバラで、必要な情報を探すのに時間がかかる
- 更新頻度や情報の鮮度がわかりにくい


サービスURL: 
**https://trail-info.jp/**


## このサービスの効果
1. **登山者側**
  - 複数サイトを巡回する手間が不要
  - 統一フォーマットで比較しやすい
  - 危険情報の見落としリスクが減る

2. **情報源サイト側**
  - 自分たちが発信した情報がより多くの登山者に届く
  - trail-info.jpからのリンクで公式サイトへの流入が期待できる
  - 個別サイトでは実現困難な「横断検索・比較」が可能になる


本サービスは登山コミュニティ内でリリースされ、ユーザーから高評価を得ています。

## スクリーンショット

<p>
  <img src="docs/images/screenshot-desktop.png" width="600" alt="デスクトップ版">
  <img src="docs/images/screenshot-mobile.png" width="180" alt="モバイル版">
</p>

## 特徴

- 自動収集: 公的機関サイトを定期的にスクレイピングし、最新情報を取得
- AI構造化: LLM（Gemini/DeepSeek/GPT）が非構造化テキストから山名・登山道名・状況等を抽出
- 名寄せ処理: RapidFuzz + SudachiPyによるテキスト類似度計算で、同一情報の重複を防止
- コスト最適化: SHA-256ハッシュによる変更検知で、更新があった情報源のみAI処理

## データフロー

```
公的機関サイト → スクレイピング → 変更検知 → AI構造化 → レコード照合 → DB保存 → Web表示
```

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Backend | Django 6.0, PostgreSQL |
| Frontend | Tailwind CSS 4.x, Vite |
| Data Collection | httpx, trafilatura |
| AI Processing | Gemini API, DeepSeek API, OpenAI API, Pydantic |
| Text Matching | RapidFuzz, SudachiPy |
| Infrastructure | Cloud Run, Supabase, Cloudflare, Docker |

## 実装の詳細

- 自前実装のプロンプト管理システム
  - 共通プロンプトと情報源ごとの個別プロンプトを分離して管理しLLMを呼び出すことで、様々な情報源に対し同一形式のフォーマットで出力することが可能です。
  - Django管理画面から情報源を新規登録することで、命名規則に基づき個別プロンプトファイルが自動生成されます。

- 形式の異なるサイトの情報の正規化について
  - **❌️課題:** LLMによる構造化出力（データフォーマットの統一）だけでは、同一カラム内での情報の精度に問題がありました。
  - temperature=0.0でもマイナーな登山道名からの山名推測の揺らぎは大きく、当初は元サイトに軽微な変更が生じるだけで元データとの同定が困難となる状況でした。
  - **✅解決策:** 前提となるLLM出力についてはグラウンディングツール（Google検索）利用で一定程度収束しました。名寄せについては、Sudachipy（日本語形態素解析ツール）でトークン化した後、Rapidfuzz（編集距離計算ライブラリ）を用いてカラムごとに異なるパラメータの設定をした上で類似度計算を行います。
  - 結果、異なるLLMクライアントによる出力結果同士でも名寄せ精度99％に至り、安定運用の目処が立ちました。
 
- LLM呼び出しコストの削減
  - 決定論的アルゴリズムでHTML本文を抽出するtrafilaturaをバージョン固定で用い、そこで処理された情報をSHA-256ハッシュ化しDBへ保存します。
  - 次回バッチ処理実行時はまずこのハッシュ値と比較し、更新有無を確認。なければLLM処理をスキップすることで月間コストを1/10程度へ削減することができました。

- バッチ処理の定期実行はCloudRunJobsで行う運用です。

## プロジェクトの成果と今後
このサービスはヤマレコ等の登山コミュニティでリリースされ、実際の利用者からは「おまい天才だな」「ありがとうありがとう」等大きな好評をいただいており、今後も運用を続けていく予定です。  
このプロジェクトを通じて、LLMを活用したデータパイプライン構築の知見を得ることができました。次のプロジェクトではRAG等の応用技術やDifyといったノーコードツールに触れてゆくことになるかもしれません。　

## 参考文献

- [trafilatura](https://trafilatura.readthedocs.io/) - Web content extraction
- [RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/) - Fuzzy string matching
- [SudachiPy](https://github.com/WorksApplications/SudachiPy) - Japanese morphological analyzer
- [Datatables](https://datatables.net/) - Interactive table plugin for jQuery
---

© 2026 HiroItozzz. All rights reserved.
