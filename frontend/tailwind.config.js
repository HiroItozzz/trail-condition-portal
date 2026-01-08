/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "/templates/**/*.html",              // base.html など
    "/trail_status_templates/**/*.html", // 登山状況アプリのテンプレート
    "./src/**/*.{js,ts}",               // frontend内のJSファイル
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}