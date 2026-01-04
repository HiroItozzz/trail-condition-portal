import './style.css'
import { fetchTrailConditions } from './api'
import type { TrailCondition } from './types'

// ステータスの絵文字マッピング
const STATUS_EMOJI: Record<string, string> = {
  CLOSURE: '🚧',
  HAZARD: '⚠️',
  SNOW: '❄️',
  ANIMAL: '🐻',
  WEATHER: '🌧️',
  FACILITY: '🏠',
  WATER: '💧',
  OTHER: '📝'
}

// 登山道状況カードを生成
function createConditionCard(condition: TrailCondition): string {
  const emoji = STATUS_EMOJI[condition.status] || '📝'
  const reportedDate = condition.reported_at
    ? new Date(condition.reported_at).toLocaleDateString('ja-JP')
    : '不明'

  return `
    <div class="condition-card">
      <div class="condition-header">
        <span class="status-badge">${emoji} ${condition.status}</span>
        <span class="area-badge">${condition.area}</span>
      </div>
      <h3>${condition.trail_name}</h3>
      <p class="mountain-name">${condition.mountain_name_raw}</p>
      <h4>${condition.title}</h4>
      <p class="description">${condition.description || '詳細なし'}</p>
      <div class="condition-footer">
        <span class="reported-date">報告日: ${reportedDate}</span>
        <a href="${condition.url1}" target="_blank" class="source-link">情報源 →</a>
      </div>
    </div>
  `
}

// アプリケーションの初期化
async function initApp() {
  const app = document.querySelector<HTMLDivElement>('#app')!

  app.innerHTML = `
    <div class="container">
      <header>
        <h1>🏔️ 登山道状況ポータル</h1>
        <p>最新の登山道情報を確認</p>
      </header>

      <div id="loading">読み込み中...</div>
      <div id="error" class="error" style="display: none;"></div>
      <div id="conditions-list"></div>
    </div>
  `

  try {
    // APIからデータ取得
    const data = await fetchTrailConditions()

    // ローディング非表示
    document.getElementById('loading')!.style.display = 'none'

    // 登山道状況一覧を表示
    const conditionsList = document.getElementById('conditions-list')!

    if (data.results.length === 0) {
      conditionsList.innerHTML = '<p>登山道状況情報がありません</p>'
    } else {
      conditionsList.innerHTML = data.results
        .map(condition => createConditionCard(condition))
        .join('')
    }
  } catch (error) {
    // エラー表示
    document.getElementById('loading')!.style.display = 'none'
    const errorDiv = document.getElementById('error')!
    errorDiv.style.display = 'block'
    errorDiv.textContent = `エラーが発生しました: ${error}`
    console.error('API error:', error)
  }
}

// アプリケーション起動
initApp()
