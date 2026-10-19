import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Descriptions, Row, Select, Space, Spin, Table, Typography, message } from 'antd'
import { ExperimentOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { api } from '../services/api'
import type { BacktestResponse, Metrics, ModelPerformance } from '../types/api'

type ModelModality = 'mri' | 'ct' | 'xray'

const modelLabels: Record<string, string> = {
  weekly_naive_baseline: 'Наївний прогноз за попереднім тижнем',
  linear_regression: 'Лінійна регресія',
  random_forest: 'Випадковий ліс',
  gradient_boosting: 'Градієнтний бустинг',
}

const featureLabels: Record<string, string> = {
  day_of_week: 'День тижня',
  month: 'Місяць',
  week_of_year: 'Тиждень року',
  is_weekend: 'Вихідний',
  day_of_year_sin: 'Річний цикл (sin)',
  day_of_year_cos: 'Річний цикл (cos)',
  lag_1: 'Значення 1 день тому',
  lag_7: 'Значення 7 днів тому',
  lag_14: 'Значення 14 днів тому',
  rolling_7: 'Середнє за 7 днів',
  rolling_14: 'Середнє за 14 днів',
  rolling_30: 'Середнє за 30 днів',
  is_holiday: 'Святковий день',
  day_before_holiday: 'День перед святом',
  day_after_holiday: 'День після свята',
  days_to_holiday: 'Днів до найближчої святкової дати',
  days_since_holiday: 'Днів після найближчої святкової дати',
}

export default function ModelPerformancePage() {
  const [performance, setPerformance] = useState<ModelPerformance | null>(null)
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null)
  const [modality, setModality] = useState<ModelModality>('mri')
  const [loading, setLoading] = useState(true)
  const [training, setTraining] = useState(false)
  const [error, setError] = useState('')
  const [messageApi, contextHolder] = message.useMessage()

  const loadPerformance = () => {
    setLoading(true)
    setError('')
    Promise.all([api.performance(), api.backtest()])
      .then(([performanceData, backtestData]) => {
        setPerformance(performanceData)
        setBacktest(backtestData)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(loadPerformance, [])

  const current = performance?.modalities[modality]
  const currentBacktest = backtest?.modalities[modality]
  const rows = useMemo(
    () => (Object.entries(current?.metrics ?? {}) as [string, Metrics][]).map(([model, metrics]) => ({ model, modelLabel: modelLabels[model] ?? model, ...metrics })),
    [current],
  )
  const featureImportance = useMemo(
    () => (current?.feature_importance ?? []).slice(0, 12).map((item) => ({ ...item, featureLabel: featureLabels[item.feature] ?? item.feature })),
    [current],
  )

  const handleTrain = async () => {
    setTraining(true)
    try {
      await api.train()
      messageApi.success('Навчання моделей завершено.')
      loadPerformance()
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : 'Навчання не вдалося.')
    } finally {
      setTraining(false)
    }
  }

  return (
    <>
      {contextHolder}
      <div className="toolbar-row">
        <PageHeader
          title="Моделі машинного навчання"
        />
        <Select<ModelModality>
          value={modality}
          onChange={setModality}
          style={{ minWidth: 160 }}
          options={[
            { value: 'mri', label: 'МРТ' },
            { value: 'ct', label: 'КТ' },
            { value: 'xray', label: 'Рентген' },
          ]}
        />
      </div>

      <Space className="model-actions">
        <Button type="primary" icon={<ExperimentOutlined />} loading={training} onClick={handleTrain}>Навчити моделі</Button>
        <Button icon={<ReloadOutlined />} onClick={loadPerformance}>Оновити</Button>
      </Space>

      {error && (
        <Alert
          type="warning"
          showIcon
          message="Дані оцінки моделей недоступні"
          description={`${error} Якщо це перший запуск v4, натисніть «Навчити моделі».`}
        />
      )}

      {loading ? <div className="center-state"><Spin size="large" /></div> : current && (
        <>
          <Card bordered={false} className="panel-card model-summary">
            <Descriptions title={`Обрана модель — ${current.label}`} column={{ xs: 1, sm: 2 }}>
              <Descriptions.Item label="Алгоритм"><Typography.Text strong>{modelLabels[current.model_name] ?? current.model_name}</Typography.Text></Descriptions.Item>
              <Descriptions.Item label="Святкові ознаки">{current.uses_holiday_features ? 'Використовуються' : 'Не використовуються у фінальній моделі'}</Descriptions.Item>
              <Descriptions.Item label="MAE крос-валідації">{current.cv_mae.toFixed(2)}</Descriptions.Item>
              <Descriptions.Item label="Рядків для навчання">{current.records_used}</Descriptions.Item>
              <Descriptions.Item label="Навчальна частина">{current.train_rows_for_evaluation}</Descriptions.Item>
              <Descriptions.Item label="Тестова частина">{current.test_rows}</Descriptions.Item>
              <Descriptions.Item label="Тестовий період">{current.test_start} — {current.test_end}</Descriptions.Item>
              <Descriptions.Item label="Останнє навчання">{performance?.trained_at ? new Date(performance.trained_at).toLocaleString('uk-UA') : '—'}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Row gutter={[16, 16]} className="section-row">
            <Col xs={12} xl={6}><StatCard title="MAE" value={current.selected_metrics.mae} precision={2} /></Col>
            <Col xs={12} xl={6}><StatCard title="RMSE" value={current.selected_metrics.rmse} precision={2} /></Col>
            <Col xs={12} xl={6}><StatCard title="MAPE" value={current.selected_metrics.mape} precision={2} suffix="%" /></Col>
            <Col xs={12} xl={6}><StatCard title="R²" value={current.selected_metrics.r2} precision={3} /></Col>
          </Row>

          <Card title="Фактичні та прогнозовані значення — тестовий період" bordered={false} className="panel-card section-row">
            <div className="chart-wrap tall">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={currentBacktest?.points ?? []}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" minTickGap={28} tickFormatter={(value) => value.slice(5)} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="actual" name="Фактичне" stroke="#1677ff" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="predicted" name="Прогноз" stroke="#fa8c16" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Row gutter={[16, 16]} className="section-row">
            <Col xs={24} xl={14}>
              <Card title="Порівняння моделей" bordered={false} className="panel-card">
                <Table
                  rowKey="model"
                  pagination={false}
                  dataSource={rows}
                  scroll={{ x: 700 }}
                  columns={[
                    { title: 'Модель', dataIndex: 'modelLabel' },
                    { title: 'MAE', dataIndex: 'mae', render: (v: number) => Number(v).toFixed(2) },
                    { title: 'RMSE', dataIndex: 'rmse', render: (v: number) => Number(v).toFixed(2) },
                    { title: 'MAPE', dataIndex: 'mape', render: (v: number) => `${Number(v).toFixed(2)}%` },
                    { title: 'R²', dataIndex: 'r2', render: (v: number) => Number(v).toFixed(3) },
                  ]}
                />
              </Card>
            </Col>
            <Col xs={24} xl={10}>
              <Card title="Важливість ознак" bordered={false} className="panel-card">
                <div className="chart-wrap tall">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={featureImportance} layout="vertical" margin={{ left: 30 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="featureLabel" width={145} />
                      <Tooltip />
                      <Bar dataKey="importance" name="Важливість" fill="#1677ff" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
          </Row>

          <Card title="Експеримент: чи допомагають святкові ознаки?" bordered={false} className="panel-card section-row">
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}><StatCard title="MAE зі святами" value={current.holiday_comparison.with_holidays.mae} precision={2} /></Col>
              <Col xs={24} md={8}><StatCard title="MAE без свят" value={current.holiday_comparison.without_holidays.mae} precision={2} /></Col>
              <Col xs={24} md={8}><StatCard title="Зміна MAE" value={current.holiday_comparison.mae_improvement_percent} precision={2} suffix="%" /></Col>
            </Row>

          </Card>
        </>
      )}
    </>
  )
}
