# トレイルインフォ ロゴスタイリングアイデア

セレクタ: `.logo-link h1`

## 1. グラデーション文字
```css
background: linear-gradient(135deg, #1e40af, #3b82f6);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;
```

## 2. シャドウで立体感
```css
text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
```

## 3. レタースペーシング調整
```css
letter-spacing: -0.05em; /* 詰める */
letter-spacing: 0.1em;   /* 広げる */
```

## 4. アンダーラインアクセント
```css
border-bottom: 3px solid #3b82f6;
display: inline-block;
padding-bottom: 4px;
```

## 5. 背景ハイライト
```css
background: rgba(59, 130, 246, 0.1);
padding: 8px 12px;
border-radius: 8px;
```

## 6. アイコン追加（CSS疑似要素）
```css
&::before {
  content: '🏔️';
  margin-right: 8px;
}
```

## 組み合わせ例

グラデーション + レタースペーシング + 軽いシャドウ:
```css
.logo-link h1 {
    background: linear-gradient(135deg, #1e3a5f, #2563eb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.05));
}
```
