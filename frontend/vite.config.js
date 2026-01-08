import { defineConfig } from 'vite'
import path from 'path'

export default defineConfig({
  // 開発サーバーの設定
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
  build: {
    // 生成されたファイルを Django の static/dist に同期される場所に書き出す
    outDir: 'dist', 
    assetsDir: '', // 余計なフォルダ分けをせず直下に置く設定
    rollupOptions: {
      // エントリーポイント（元となるCSSファイル）を指定
      input: path.resolve(__dirname, 'src/main.css'),
      output: {
        // ファイル名を固定（Django側で読み込みやすくするため）
        entryFileNames: `[name].js`,
        chunkFileNames: `[name].js`,
        assetFileNames: `[name].[ext]`,
      },
    },
  },
})