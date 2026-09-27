# frontend/

- `src/main.ts` / `api.ts` / `types.ts` と `index.html` を直しても、本番の画面は変わらない。これらは開発用サーバーでしか使われない。本番の画面は Django テンプレート（`templates/`）。
- ビルドの入口は `src/main.css` だけ（`vite.config.js`）。Tailwind で処理した CSS が `dist/main.css` になり、`static/dist/` から読み込まれる。
- `main.ts` は外部から取得したデータをエスケープせずに `innerHTML` へ入れている。ビルドの対象に加える前に、`textContent` を使うなどして直す。
