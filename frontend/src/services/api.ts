import { clearAccessToken, getAccessToken, setAccessToken } from './authStorage'
import type {
  AnomalyResponse,
  AuthConfig,
  BacktestResponse,
  CurrentUser,
  DailyVisit,
  DatasetInfo,
  DatasetUploadResponse,
  ForecastResponse,
  HolidayImpact,
  Modality,
  ModalitySummary,
  ModelPerformance,
  MonthlyVisit,
  MultiDailyVisit,
  SeasonalityPoint,
  Summary,
  TokenResponse,
  TrendResponse,
  WeekdayAverage,
} from '../types/api'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function parseError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null)
  return body?.detail ?? body?.message ?? `Помилка запиту: ${response.status}`
}

async function refreshToken(): Promise<string | null> {
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) {
    clearAccessToken()
    return null
  }
  const data = (await response.json()) as TokenResponse
  setAccessToken(data.access_token)
  return data.access_token
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })

  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    const refreshed = await refreshToken()
    if (refreshed) return request<T>(path, init, false)
  }
  if (!response.ok) throw new Error(await parseError(response))
  return response.json() as Promise<T>
}

export const authApi = {
  config: () => request<AuthConfig>('/auth/config'),
  me: () => request<CurrentUser>('/auth/me'),
  async exchange(code: string, codeVerifier: string, redirectUri: string): Promise<TokenResponse> {
    const response = await fetch(`${API_URL}/auth/exchange`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, code_verifier: codeVerifier, redirect_uri: redirectUri }),
    })
    if (!response.ok) throw new Error(await parseError(response))
    const data = (await response.json()) as TokenResponse
    setAccessToken(data.access_token)
    return data
  },
  async tryRefresh(): Promise<boolean> {
    return Boolean(await refreshToken())
  },
  async logout(): Promise<void> {
    try {
      await request('/auth/logout', { method: 'POST' }, false)
    } finally {
      clearAccessToken()
    }
  },
}

const q = (modality: Modality) => `modality=${encodeURIComponent(modality)}`

export const api = {
  modalitiesSummary: () => request<ModalitySummary[]>('/analytics/modalities-summary'),
  summary: (modality: Modality = 'all') => request<Summary>(`/analytics/summary?${q(modality)}`),
  daily: (modality: Modality = 'all') => request<DailyVisit[]>(`/analytics/daily?${q(modality)}`),
  monthly: (modality: Modality = 'all') => request<MonthlyVisit[]>(`/analytics/monthly?${q(modality)}`),
  weekdays: (modality: Modality = 'all') => request<WeekdayAverage[]>(`/analytics/weekdays?${q(modality)}`),
  trends: (modality: Modality = 'all', days = 180) => request<TrendResponse>(`/analytics/trends?${q(modality)}&days=${days}`),
  seasonality: (modality: Modality = 'all') => request<SeasonalityPoint[]>(`/analytics/seasonality?${q(modality)}`),
  anomalies: (modality: Modality = 'all', threshold = 2.5) => request<AnomalyResponse>(`/analytics/anomalies?${q(modality)}&threshold=${threshold}`),
  holidayImpact: (modality: Modality = 'all') => request<HolidayImpact>(`/analytics/holiday-impact?${q(modality)}`),
  forecast: (days = 7) => request<ForecastResponse>(`/ml/forecast?days=${days}`),
  performance: () => request<ModelPerformance>('/ml/performance'),
  backtest: () => request<BacktestResponse>('/ml/backtest'),
  datasetInfo: () => request<DatasetInfo>('/data/info'),
  datasetPreview: (limit = 10) => request<MultiDailyVisit[]>(`/data/preview?limit=${limit}`),
  async uploadDataset(file: File): Promise<DatasetUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return request<DatasetUploadResponse>('/data/upload', { method: 'POST', body: formData })
  },
  train: () => request<ModelPerformance>('/ml/train', { method: 'POST' }),
}
