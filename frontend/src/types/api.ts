export type Modality = 'all' | 'mri' | 'ct' | 'xray'

export interface AuthConfig {
  authorization_endpoint: string
  authorization_url_template: string
  client_id: string
  redirect_uri: string
  scope: string
  code_challenge_method: 'S256'
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface CurrentUser {
  username: string
  email: string | null
  display_name: string
  roles: string[]
  primary_role: 'admin' | 'manager'
}

export interface Summary {
  modality: Modality
  modality_label: string
  start_date: string
  end_date: string
  days: number
  total_visits: number
  daily_average: number
  median: number
  minimum: number
  maximum: number
  std_dev: number
  latest_7_day_average: number
  latest_30_day_average: number
}

export interface ModalitySummary {
  modality: Modality
  label: string
  total: number
  daily_average: number
  latest: number
}

export interface DailyVisit {
  date: string
  patients: number
}

export interface MultiDailyVisit {
  date: string
  mri: number
  ct: number
  xray: number
  total: number
}

export interface MonthlyVisit {
  month: string
  total: number
  average: number
  maximum: number
  minimum: number
}

export interface WeekdayAverage {
  day: string
  day_number: number
  average_patients: number
}

export interface TrendPoint {
  date: string
  patients: number
  rolling_7: number
  rolling_30: number
}

export interface TrendResponse {
  modality: Modality
  window_days: number
  direction: 'increasing' | 'decreasing' | 'stable'
  direction_label: string
  change_percent: number
  latest_7_day_average: number
  latest_30_day_average: number
  points: TrendPoint[]
}

export interface SeasonalityPoint {
  month_number: number
  month: string
  average_patients: number
  observations: number
}

export interface AnomalyPoint {
  date: string
  patients: number
  day: string
  expected_weekday_average: number
  z_score: number
  type: 'high' | 'low'
  type_label: string
}

export interface AnomalyResponse {
  threshold: number
  count: number
  anomalies: AnomalyPoint[]
}

export interface HolidayGroupStats {
  observations: number
  average_patients: number | null
}

export interface HolidayImpact {
  modality: Modality
  regular_days: HolidayGroupStats
  holidays: HolidayGroupStats
  day_before_holiday: HolidayGroupStats
  day_after_holiday: HolidayGroupStats
}

export interface ForecastPoint {
  date: string
  mri: number
  ct: number
  xray: number
  total: number
  calendar_event: string | null
}

export interface ForecastResponse {
  days: number
  forecast: ForecastPoint[]
}

export interface Metrics {
  mae: number
  rmse: number
  mape: number
  r2: number
}

export interface FeatureImportance {
  feature: string
  importance: number
}

export interface ModalityPerformance {
  label: string
  model_name: string
  uses_holiday_features: boolean
  selected_features: string[]
  selection_method: string
  cv_mae: number
  records_used: number
  train_rows_for_evaluation: number
  test_rows: number
  test_start: string
  test_end: string
  metrics: Record<string, Metrics>
  selected_metrics: Metrics
  feature_importance: FeatureImportance[]
  holiday_comparison: {
    selected_variant: 'with_holidays' | 'without_holidays'
    best_with_holidays_model_name: string
    best_without_holidays_model_name: string
    with_holidays: Metrics
    without_holidays: Metrics
    mae_improvement_percent: number
    cv_mae_with_holidays: number
    cv_mae_without_holidays: number
  }
}

export interface ModelPerformance {
  version: string
  trained_at: string
  records_total: number
  base_features: string[]
  holiday_features: string[]
  modalities: Record<'mri' | 'ct' | 'xray', ModalityPerformance>
}

export interface BacktestPoint {
  date: string
  actual: number
  predicted: number
  error: number
}

export interface ModalityBacktest {
  model_name: string
  test_start: string
  test_end: string
  points: BacktestPoint[]
}

export interface BacktestResponse {
  generated_at: string
  modalities: Record<'mri' | 'ct' | 'xray', ModalityBacktest>
}

export interface DatasetInfo {
  filename: string
  rows: number
  start_date: string
  end_date: string
  totals: { mri: number; ct: number; xray: number; total: number }
  calendar_gap_days: number
  calendar_coverage_percent: number
  model_trained_at: string | null
  model_needs_retraining: boolean
}

export interface DatasetQualityReport {
  input_format: 'wide' | 'long'
  original_rows: number
  saved_daily_rows: number
  invalid_date_rows: number
  invalid_count_rows: number
  negative_count_rows: number
  duplicate_date_rows: number
  calendar_gap_days: number
  start_date: string
  end_date: string
  totals: { mri: number; ct: number; xray: number; total: number }
}

export interface DatasetUploadResponse {
  message: string
  source_filename: string
  saved_as: string
  backup_created: string | null
  model_needs_retraining: boolean
  quality: DatasetQualityReport
}
