# Trail Condition Portal

登山道の危険情報を公的機関から自動収集・統合表示するWebアプリケーション

## 概要

- 環境省、自治体、警察等の公式サイトから登山道危険情報を自動収集
- AI（DeepSeek/Gemini）による情報の構造化・正規化
- Django + PostgreSQLによる管理・表示

## 技術スタック

- **Backend**: Django 6.0, PostgreSQL
- **frontend**: Vite, TypeScript, TailwindCSS 4.x
- **Data Collection**: httpx, trafilatura, RapidFuzz, SudachiPy
- **AI Processing**: DeepSeek API, Gemini API, OpenAI API, Pydantic, LangSmith
- **Task Scheduling**: django-apscheduler
- **Infrastructure**: Docker, uv

## 開発環境

```bash
# コンテナ起動
docker compose up -d

# アプリケーション実行
docker compose exec web uv run manage.py runserver
```

## データフロー

1. **収集**: 公的機関サイトから自動スクレイピング
2. **正規化**: AIが危険レベル・エリア等を構造化
3. **保存**: PostgreSQLに原文+正規化データを保存
4. **表示**: 管理画面・API経由で提供

## 参考文献
- https://trafilatura.readthedocs.io/en/latest/
- https://rapidfuzz.github.io/RapidFuzz/index.html
- https://github.com/WorksApplications/SudachiPy