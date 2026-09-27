# templates/

本番の画面。`static/js/` の素の JavaScript と組み合わせて動く。

- CSS は 2 つ読み込んでいる（`trail_status/base.html`）。`static/dist/main.css` は `frontend/` を Tailwind でビルドしたもの、`static/css/style.css` は手書き。見た目を変えるときは、どちらに書くかを先に確認する。
- 外部から取得したデータを表示しているため、Django の自動エスケープに任せる。`|safe` や `mark_safe` は使わない。
