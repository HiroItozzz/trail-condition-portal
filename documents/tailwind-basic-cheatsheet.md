# Tailwind CSS 基本チートシート

## 文字サイズ
```html
<div class="text-xs">極小</div>
<div class="text-sm">小</div>
<div class="text-base">標準</div>
<div class="text-lg">大</div>
<div class="text-xl">特大</div>
<div class="text-2xl">超特大</div>
<div class="text-3xl">巨大</div>
```

## 文字揃え
```html
<div class="text-left">左揃え</div>
<div class="text-center">中央揃え</div>
<div class="text-right">右揃え</div>
```

## 文字の太さ・装飾
```html
<div class="font-bold">太字</div>
<div class="font-semibold">中太字</div>
<div class="font-normal">標準</div>
<div class="font-light">細字</div>
<div class="underline">下線</div>
<div class="italic">斜体</div>
<div class="text-blue-500">青文字</div>
<div class="text-red-500">赤文字</div>
<div class="text-gray-500">灰色文字</div>
```

## 横並び + 配置パターン（超重要）
```html
<!-- 基本の横並び -->
<div class="flex">
  <div>左</div>
  <div>右</div>
</div>

<!-- 左右に分かれて配置 -->
<div class="flex justify-between">
  <div>左側</div>
  <div>右側</div>
</div>

<!-- 中央寄せ -->
<div class="flex justify-center">
  <div>中央</div>
</div>

<!-- 等間隔 -->
<div class="flex justify-around">
  <div>A</div>
  <div>B</div>
  <div>C</div>
</div>

<!-- 要素間に隙間 -->
<div class="flex gap-4">
  <div>A</div>
  <div>B</div>
</div>

<!-- 上下中央揃え -->
<div class="h-24 flex items-center justify-center">
  中央に配置
</div>

<!-- 縦並び（flexの方向変更） -->
<div class="flex flex-col">
  <div>上</div>
  <div>下</div>
</div>
```

## 余白・間隔
```html
<!-- padding（内側の余白） -->
<div class="p-4">全方向 padding</div>
<div class="px-4">左右 padding</div>
<div class="py-2">上下 padding</div>
<div class="pt-2 pb-4">上2, 下4</div>

<!-- margin（外側の余白） -->
<div class="m-4">全方向 margin</div>
<div class="mx-auto">左右中央寄せ</div>
<div class="mt-8">上 margin</div>

<!-- 数字 = 4px単位（1=4px, 2=8px, 4=16px, 8=32px） -->
```

## サイズ指定
```html
<!-- 幅 -->
<div class="w-full">画面幅100%</div>
<div class="w-1/2">50%</div>
<div class="w-64">256px固定</div>
<div class="max-w-md">最大幅制限</div>

<!-- 高さ -->
<div class="h-32">128px</div>
<div class="h-screen">画面高さ100%</div>
<div class="min-h-screen">最低画面高さ</div>
```

## 背景・境界線
```html
<!-- 背景色 -->
<div class="bg-blue-500">青背景</div>
<div class="bg-gray-100">薄灰色背景</div>
<div class="bg-white">白背景</div>

<!-- 境界線 -->
<div class="border">境界線</div>
<div class="border-2">太い境界線</div>
<div class="border-gray-300">灰色境界線</div>
<div class="rounded">角丸</div>
<div class="rounded-lg">大きい角丸</div>
```

## レスポンシブ（画面サイズ対応）
```html
<!-- スマホ: 縦並び、PC: 横並び -->
<div class="flex flex-col md:flex-row">
  <div>内容1</div>
  <div>内容2</div>
</div>

<!-- スマホ: 小さい文字、PC: 大きい文字 -->
<div class="text-sm md:text-lg">レスポンシブ文字</div>

<!-- sm: 640px以上, md: 768px以上, lg: 1024px以上 -->
```

## よく使う組み合わせパターン
```html
<!-- カード風ボックス -->
<div class="bg-white p-6 rounded-lg border shadow">
  カード内容
</div>

<!-- ボタン風 -->
<div class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
  ボタン
</div>

<!-- 中央配置コンテナ -->
<div class="max-w-4xl mx-auto p-4">
  メインコンテンツ
</div>

<!-- ヘッダー風 -->
<div class="bg-white border-b px-4 py-3 flex justify-between items-center">
  <div class="font-bold">ロゴ</div>
  <div>メニュー</div>
</div>
```

## 覚えておくべき法則

1. **親に`flex`をつけて子要素を制御**
2. **数字は4px単位**（1=4px, 2=8px, 4=16px）
3. **レスポンシブは`md:`プレフィックス**
4. **`mx-auto`で中央寄せ**
5. **`gap-4`で要素間の隙間**

この基本パターンで90%のレイアウトは完成します。