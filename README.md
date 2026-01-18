# Trail Condition Portal

登山道の危険情報を公的機関から自動収集・統合表示するWebアプリケーション
- https://trail-info.jp/

## 概要

- 地方自治体、省庁等の公式サイトから登山道危険情報を自動収集
- AI（Gemini/GPT/DeepSeek）による情報の構造化
- RapidFuzz + SudachiPyによるテキスト類似度計算・名寄せ処理
- サイト内容変更の有無確認（SHA-256ハッシュ）によるAI処理コストの最適化
- Django + PostgreSQLによる管理・表示

## 技術スタック

- **Backend**: Django 6.0, PostgreSQL
- **frontend**: TailwindCSS 4.x, JavaScript, Vite
- **Data Collection**: httpx, trafilatura, RapidFuzz, SudachiPy
- **AI Processing**: Gemini API, Pydantic, LangSmith (+ OpenAI API, DeepSeek API)
- **Infrastructure**: Cloudflare, Cloud Run, Supabase, Docker, uv

## データフロー

1. **スクレイピング**: 公的機関サイトから登山道情報を取得・本文抽出
2. **変更検知**: ハッシュ比較で更新があった情報源のみ次へ進む
3. **AI構造化**: LLMが非構造化テキストから山名・登山道名・状況等を抽出
4. **レコード照合**: 類似度計算で既存データと同一性を判定（更新 or 新規作成）
5. **データ保存**: 原文とAI抽出結果をPostgreSQLに永続化
6. **表示**: Django管理画面で統合情報を閲覧可能

## 参考文献
- https://trafilatura.readthedocs.io/en/latest/
- https://rapidfuzz.github.io/RapidFuzz/index.html
- https://github.com/WorksApplications/SudachiPy