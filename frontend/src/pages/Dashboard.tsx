import { useEffect, useMemo, useState } from 'react'
import { Alert, Card, Col, Row, Spin, Table, Typography } from 'antd'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../services/api'
import type { DailyVisit, ForecastPoint, ModalitySummary, Summary } from '../types/api'
import StatCard from '../components/StatCard'
import PageHeader from '../components/PageHeader'

const uaDate = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('uk-UA', { weekday: 'short', month: 'short', day: 'numeric' })

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [modalitySummary, setModalitySummary] = useState<ModalitySummary[]>([])
  const [daily, setDaily] = useState<DailyVisit[]>([])
  const [forecast, setForecast] = useState<ForecastPoint[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.summary('all'), api.modalitiesSummary(), api.daily('all'), api.forecast(7)])
      .then(([summaryData, modalities, dailyData, forecastData]) => {
        setSummary(summaryData)
        setModalitySummary(modalities)
        setDaily(dailyData)
        setForecast(forecastData.forecast)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const recentDaily = useMemo(() => daily.slice(-90), [daily])
  const getLatest = (modality: string) => modalitySummary.find((item) => item.modality === modality)?.latest ?? 0

  if (loading) return <div className="center-state"><Spin size="large" /></div>

  return (
    <>
      <PageHeader title="Панель керування" description="Поточне навантаження, історичний тренд і прогноз на найближчі сім днів." />
      {error && <Alert type="error" showIcon message="Не вдалося завантажити панель" description={error} />}

      <Row gutter={[16, 16]}>
        <Col xs={12} xl={6}><StatCard title="Усього за останній день" value={getLatest('all')} suffix="обст." /></Col>
        <Col xs={12} xl={6}><StatCard title="МРТ" value={getLatest('mri')} /></Col>
        <Col xs={12} xl={6}><StatCard title="КТ" value={getLatest('ct')} /></Col>
        <Col xs={12} xl={6}><StatCard title="Рентген" value={getLatest('xray')} /></Col>
      </Row>

      {summary && (
        <Row gutter={[16, 16]} className="section-row">
          <Col xs={12} xl={6}><StatCard title="Середнє за день" value={summary.daily_average} precision={1} /></Col>
          <Col xs={12} xl={6}><StatCard title="Середнє за 7 днів" value={summary.latest_7_day_average} precision={1} /></Col>
          <Col xs={12} xl={6}><StatCard title="Середнє за 30 днів" value={summary.latest_30_day_average} precision={1} /></Col>
          <Col xs={12} xl={6}><StatCard title="Максимум за день" value={summary.maximum} /></Col>
        </Row>
      )}

      <Row gutter={[16, 16]} className="section-row">
        <Col xs={24} xl={15}>
          <Card title="Загальна кількість обстежень — останні 90 днів" bordered={false} className="panel-card">
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={recentDaily}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" minTickGap={28} tickFormatter={(value) => value.slice(5)} />
                  <YAxis allowDecimals={false} />
                  <Tooltip labelFormatter={(value) => uaDate(String(value))} formatter={(value) => [value, 'Обстеження']} />
                  <Area type="monotone" dataKey="patients" stroke="#1677ff" fill="#1677ff" fillOpacity={0.12} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
        <Col xs={24} xl={9}>
          <Card title="Прогноз на 7 днів" bordered={false} className="panel-card">
            <Table
              rowKey="date" size="small" pagination={false} dataSource={forecast}
              scroll={{ x: 500 }}
              columns={[
                { title: 'Дата', dataIndex: 'date', render: (value: string) => uaDate(value) },
                { title: 'Подія', dataIndex: 'calendar_event', render: (value: string | null) => value ?? '—' },
                { title: 'МРТ', dataIndex: 'mri', align: 'right' },
                { title: 'КТ', dataIndex: 'ct', align: 'right' },
                { title: 'Рентген', dataIndex: 'xray', align: 'right' },
                { title: 'Усього', dataIndex: 'total', align: 'right', render: (value: number) => <Typography.Text strong>{value}</Typography.Text> },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </>
  )
}
