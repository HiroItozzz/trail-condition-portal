/**
 * API型定義
 * Django REST FrameworkのTrailConditionSerializerに対応
 */

export type StatusType =
  | 'CLOSURE'   // 通行止め・閉鎖
  | 'HAZARD'    // 危険箇所・通行注意
  | 'SNOW'      // 積雪・アイスバーン
  | 'ANIMAL'    // 動物出没
  | 'WEATHER'   // 気象警報
  | 'FACILITY'  // 施設情報
  | 'WATER'     // 水場状況
  | 'OTHER'     // その他

export type AreaName =
  | 'OKUTAMA'
  | 'CHICHIBU'
  | 'TANZAWA'
  | 'FUJI'
  | 'YATSUGATAKE'
  | 'NANTAISAN'
  | 'NIKKO'
  | 'OTHER'

export interface TrailCondition {
  id: number
  source: number | null
  url1: string
  trail_name: string
  mountain_name_raw: string
  title: string
  description: string
  reported_at: string | null
  resolved_at: string | null
  status: StatusType
  area: AreaName
  reference_URL: string
  comment: string
  mountain_group: number | null
  ai_model: string
  prompt_file: string
  ai_config: Record<string, any> | null
  disabled: boolean
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface DataSource {
  id: number
  name: string
  organization_type: string
  prefecture_code: string
  prompt_key: string
  url1: string
  url2: string
  data_format: string
  content_hash: string
  last_scraped_at: string | null
  created_at: string
  updated_at: string
}
