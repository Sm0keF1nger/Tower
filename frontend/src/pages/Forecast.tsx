import { useEffect, useMemo, useState } from 'react'
import { Alert, Card, Radio, Select, Spin, Table } from 'antd'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import PageHeader from '../components/PageHeader'
import { api } from '../services/api'
import type { ForecastPoint, Modality } from '../types/api'

const modalityOptions = [
  { value: 'all', label: 'Усі обстеження' },
  { value: 'mri', label: 'МРТ' },
  { value: 'ct', label: 'КТ' },
  { value: 'xray', label: 'Рентген' },
]

const dataKeyFor = (modality: Modality) => modality === 'all' ? 'total' : modality
const labelFor = (modality: Modality) => modalityOptions.find((item) => item.value === modality)?.label ?? modality

export default function Forecast() {
  const [days, setDays] = useState(7)
  const [modality, setModality] = useState<Modality>('all')
  const [forecast, setForecast] = useState<ForecastPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    api.forecast(days)
      .then((result) => setForecast(result.forecast))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [days])

  const tableColumns = useMemo(() => {
    if (modality !== 'all') {
      return [
        { title: 'Дата', dataIndex: 'date' },
        { title: 'Календарна подія', dataIndex: 'calendar_event', render: (value: string | null) => value ?? '—' },
        { title: labelFor(modality), dataIndex: dataKeyFor(modality), align: 'right' as const },
      ]
    }
    return [
      { title: 'Дата', dataIndex: 'date' },
      { title: 'Календарна подія', dataIndex: 'calendar_event', render: (value: string | null) => value ?? '—' },
      { title: 'МРТ', dataIndex: 'mri', align: 'right' as const },
      { title: 'КТ', dataIndex: 'ct', align: 'right' as const },
      { title: 'Рентген', dataIndex: 'xray', align: 'right' as const },
      { title: 'Усього', dataIndex: 'total', align: 'right' as const },
    ]
  }, [modality])

  return (
    <>
      <div className="toolbar-row">
        <PageHeader
          title="Прогноз"
          description="Прогноз кількості МРТ, КТ та рентген-обстежень. Система перевіряє святкові ознаки під час навчання та використовує їх для кожного типу лише тоді, коли вони покращують часову валідацію."
        />
        <div className="forecast-controls">
          <Select value={modality} onChange={setModality} options={modalityOptions} style={{ minWidth: 180 }} />
          <Radio.Group value={days} onChange={(event) => setDays(event.target.value)} buttonStyle="solid">
            <Radio.Button value={7}>7 днів</Radio.Button>
            <Radio.Button value={14}>14 днів</Radio.Button>
            <Radio.Button value={30}>30 днів</Radio.Button>
          </Radio.Group>
        </div>
      </div>

      {error && <Alert type="error" showIcon message="Не вдалося сформувати прогноз" description={error} />}
      {loading ? <div className="center-state"><Spin size="large" /></div> : (
        <div className="forecast-grid">
          <Card title={`Прогноз: ${labelFor(modality)}`} bordered={false} className="panel-card">
            <div className="chart-wrap tall">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecast}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" minTickGap={24} tickFormatter={(value) => value.slice(5)} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  {modality === 'all' ? (
                    <>
                      <Line type="monotone" dataKey="mri" name="МРТ" stroke="#1677ff" strokeWidth={2} />
                      <Line type="monotone" dataKey="ct" name="КТ" stroke="#722ed1" strokeWidth={2} />
                      <Line type="monotone" dataKey="xray" name="Рентген" stroke="#13c2c2" strokeWidth={2} />
                      <Line type="monotone" dataKey="total" name="Усього" stroke="#fa8c16" strokeWidth={3} />
                    </>
                  ) : (
                    <Line type="monotone" dataKey={dataKeyFor(modality)} name={labelFor(modality)} stroke="#1677ff" strokeWidth={3} />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Таблиця прогнозу" bordered={false} className="panel-card">
            <Table rowKey="date" size="small" pagination={false} dataSource={forecast} columns={tableColumns} scroll={{ x: 520, y: 390 }} />
          </Card>
        </div>
      )}
    </>
  )
}
