/**
 * Django REST API クライアント
 */

import type { TrailCondition, PaginatedResponse } from './types'

const API_BASE_URL = 'http://localhost:8000/api'

/**
 * 登山道状況一覧を取得
 */
export async function fetchTrailConditions(): Promise<PaginatedResponse<TrailCondition>> {
  const response = await fetch(`${API_BASE_URL}/trail-conditions/`)

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

/**
 * 登山道状況詳細を取得
 */
export async function fetchTrailCondition(id: number): Promise<TrailCondition> {
  const response = await fetch(`${API_BASE_URL}/trail-conditions/${id}`)

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}
