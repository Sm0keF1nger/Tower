import { useEffect, useMemo, useState } from 'react'
import { Alert, Card, Col, Row, Spin, Table, Tag, Typography } from 'antd'
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
import ModalitySelect from '../components/ModalitySelect'
import { api } from '../services/api'
import type {
  AnomalyResponse,
  HolidayImpact,
  Modality,
  MonthlyVisit,
  SeasonalityPoint,
  TrendResponse,
  WeekdayAverage,
} from '../types/api'

export default function Analytics() {
  const [modality, setModality] = useState<Modality>('all')
  const [monthly, setMonthly] = useState<MonthlyVisit[]>([])
  const [weekdays, setWeekdays] = useState<WeekdayAverage[]>([])
  const [trend, setTrend] = useState<TrendResponse | null>(null)
  const [seasonality, setSeasonality] = useState<SeasonalityPoint[]>([])
  const [anomalies, setAnomalies] = useState<AnomalyResponse | null>(null)
  const [holidayImpact, setHolidayImpact] = useState<HolidayImpact | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    Promise.all([
      api.monthly(modality),
      api.weekdays(modality),
      api.trends(modality, 180),
      api.seasonality(modality),
      api.anomalies(modality, 2.5),
      api.holidayImpact(modality),
    ])
      .then(([monthlyData, weekdayData, trendData, seasonalityData, anomalyData, holidayData]) => {
        setMonthly(monthlyData)
        setWeekdays(weekdayData)
        setTrend(trendData)
        setSeasonality(seasonalityData)
        setAnomalies(anomalyData)
        setHolidayImpact(holidayData)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [modality])

  const anomalyRows = useMemo(() => anomalies?.anomalies.slice(0, 15) ?? [], [anomalies])

  return (
    <>
      <div className="toolbar-row">
        <PageHeader
          title="Аналітика"
          description="Тренди, сезонність, ковзні середні, аномалії та вплив свят на навантаження клініки."
        />
        <ModalitySelect value={modality} onChange={setModality} />
      </div>

      {error && <Alert type="error" showIcon message="Не вдалося завантажити аналітику" description={error} />}
      {loading ? <div className="center-state"><Spin size="large" /></div> : (
        <>
          {trend && (
            <Row gutter={[16, 16]}>
              <Col xs={12} xl={6}><StatCard title="Середнє за 7 днів" value={trend.latest_7_day_average} precision={1} /></Col>
              <Col xs={12} xl={6}><StatCard title="Середнє за 30 днів" value={trend.latest_30_day_average} precision={1} /></Col>
              <Col xs={12} xl={6}><StatCard title="Зміна за 30 днів" value={trend.change_percent} precision={1} suffix="%" /></Col>
              <Col xs={12} xl={6}>
                <Card bordered={false} className="stat-card text-stat-card">
                  <Typography.Text type="secondary">Поточний тренд</Typography.Text>
                  <div className="text-stat-value">{trend.direction_label}</div>
                </Card>
              </Col>
            </Row>
          )}

          <Card title="Тренд за останні 180 записів" bordered={false} className="panel-card section-row">
            <div className="chart-wrap tall">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend?.points ?? []}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" minTickGap={28} tickFormatter={(value) => value.slice(5)} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="patients" name="Щоденне значення" stroke="#91caff" dot={false} strokeWidth={1} />
                  <Line type="monotone" dataKey="rolling_7" name="Середнє за 7 днів" stroke="#1677ff" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="rolling_30" name="Середнє за 30 днів" stroke="#722ed1" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Row gutter={[16, 16]} className="section-row">
            <Col xs={24} xl={14}>
              <Card title="Кількість обстежень за місяцями" bordered={false} className="panel-card">
                <div className="chart-wrap tall">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={monthly}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="month" minTickGap={20} />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="total" name="Усього" stroke="#1677ff" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
            <Col xs={24} xl={10}>
              <Card title="Середнє за днями тижня" bordered={false} className="panel-card">
                <div className="chart-wrap tall">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={weekdays} layout="vertical" margin={{ left: 12 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="day" width={100} />
                      <Tooltip />
                      <Bar dataKey="average_patients" name="Середнє" fill="#1677ff" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} className="section-row">
            <Col xs={24} xl={12}>
              <Card title="Сезонність за календарними місяцями" bordered={false} className="panel-card">
                <div className="chart-wrap tall">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={seasonality}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="month" interval={0} angle={-28} textAnchor="end" height={72} />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="average_patients" name="Середнє" fill="#13c2c2" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card title="Вплив святкових днів" bordered={false} className="panel-card">
                <Row gutter={[12, 12]}>
                  <Col span={12}><StatCard title="Звичайні дні" value={holidayImpact?.regular_days.average_patients ?? 0} precision={1} /></Col>
                  <Col span={12}><StatCard title="Святкові дні" value={holidayImpact?.holidays.average_patients ?? 0} precision={1} /></Col>
                  <Col span={12}><StatCard title="День перед святом" value={holidayImpact?.day_before_holiday.average_patients ?? 0} precision={1} /></Col>
                  <Col span={12}><StatCard title="День після свята" value={holidayImpact?.day_after_holiday.average_patients ?? 0} precision={1} /></Col>
                </Row>
                <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0 }}>
                  Святкові ознаки включають офіційні календарні свята України, Новий рік, Різдво та сусідні до них дні.
                </Typography.Paragraph>
              </Card>
            </Col>
          </Row>

          <Card title={`Аномальні дні (${anomalies?.count ?? 0})`} bordered={false} className="panel-card section-row">
            <Table
              rowKey="date"
              size="small"
              pagination={false}
              dataSource={anomalyRows}
              scroll={{ x: 700 }}
              columns={[
                { title: 'Дата', dataIndex: 'date' },
                { title: 'День', dataIndex: 'day' },
                { title: 'Фактично', dataIndex: 'patients', align: 'right' },
                { title: 'Очікуване середнє', dataIndex: 'expected_weekday_average', align: 'right' },
                { title: 'Z-score', dataIndex: 'z_score', align: 'right' },
                {
                  title: 'Тип', dataIndex: 'type_label',
                  render: (value: string, row) => <Tag color={row.type === 'high' ? 'red' : 'blue'}>{value}</Tag>,
                },
              ]}
            />
          </Card>
        </>
      )}
    </>
  )
}
