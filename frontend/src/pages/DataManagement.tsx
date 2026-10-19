import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Descriptions, Row, Space, Spin, Table, Typography, Upload, message } from 'antd'
import { InboxOutlined, ReloadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { api } from '../services/api'
import type { DatasetInfo, DatasetUploadResponse, MultiDailyVisit } from '../types/api'

export default function DataManagement() {
  const [info, setInfo] = useState<DatasetInfo | null>(null)
  const [preview, setPreview] = useState<MultiDailyVisit[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [lastUpload, setLastUpload] = useState<DatasetUploadResponse | null>(null)
  const [error, setError] = useState('')
  const [messageApi, contextHolder] = message.useMessage()

  const load = () => {
    setLoading(true)
    setError('')
    Promise.all([api.datasetInfo(), api.datasetPreview(12)])
      .then(([dataInfo, rows]) => { setInfo(dataInfo); setPreview(rows) })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const uploadProps: UploadProps = {
    multiple: false,
    accept: '.csv,.xlsx',
    showUploadList: false,
    customRequest: async ({ file, onSuccess, onError }) => {
      setUploading(true)
      try {
        const result = await api.uploadDataset(file as File)
        setLastUpload(result)
        messageApi.success(result.message)
        onSuccess?.(result)
        load()
      } catch (err) {
        const errorValue = err instanceof Error ? err : new Error('Помилка завантаження')
        messageApi.error(errorValue.message)
        onError?.(errorValue)
      } finally {
        setUploading(false)
      }
    },
  }

  return (
    <>
      {contextHolder}
      <PageHeader
        title="Керування даними"
        description="Завантаження та перевірка щоденних даних МРТ, КТ і рентгену. Цей розділ доступний лише адміністратору."
      />
      {error && <Alert type="error" showIcon message="Не вдалося завантажити інформацію про дані" description={error} />}

      <Card bordered={false} className="panel-card">
        <Typography.Title level={4}>Формати файлу</Typography.Title>
        <Typography.Paragraph>
          Рекомендований широкий формат: <Typography.Text code>date,mri,ct,xray</Typography.Text>. Також підтримується довгий формат:
          <Typography.Text code>date,modality,patients</Typography.Text>, де технічні значення modality: mri / ct / xray (МРТ / КТ / рентген). Для кожної дати вкажіть усі три типи; якщо обстежень не було — запишіть 0.
        </Typography.Paragraph>
        <Upload.Dragger {...uploadProps} disabled={uploading}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">Перетягніть CSV/XLSX сюди або натисніть для вибору</p>
          <p className="ant-upload-hint">Поточний файл буде збережено в резервну копію перед заміною.</p>
        </Upload.Dragger>
      </Card>

      {loading ? <div className="center-state"><Spin size="large" /></div> : info && (
        <>
          <div className="toolbar-row section-row">
            <Typography.Title level={4} style={{ margin: 0 }}>Поточний набір даних</Typography.Title>
            <Button icon={<ReloadOutlined />} onClick={load}>Оновити</Button>
          </div>
          <Row gutter={[16, 16]}>
            <Col xs={12} xl={6}><StatCard title="Днів у наборі" value={info.rows} /></Col>
            <Col xs={12} xl={6}><StatCard title="МРТ — усього" value={info.totals.mri} /></Col>
            <Col xs={12} xl={6}><StatCard title="КТ — усього" value={info.totals.ct} /></Col>
            <Col xs={12} xl={6}><StatCard title="Рентген — усього" value={info.totals.xray} /></Col>
          </Row>

          <Card bordered={false} className="panel-card section-row">
            <Descriptions column={{ xs: 1, md: 2 }}>
              <Descriptions.Item label="Період">{info.start_date} — {info.end_date}</Descriptions.Item>
              <Descriptions.Item label="Покриття календаря">{info.calendar_coverage_percent}%</Descriptions.Item>
              <Descriptions.Item label="Пропущені календарні дні">{info.calendar_gap_days}</Descriptions.Item>
              <Descriptions.Item label="Усього обстежень">{info.totals.total}</Descriptions.Item>
              <Descriptions.Item label="Стан моделі">{info.model_needs_retraining ? 'Потрібне перенавчання' : 'Актуальна'}</Descriptions.Item>
              <Descriptions.Item label="Останнє навчання">{info.model_trained_at ? new Date(info.model_trained_at).toLocaleString('uk-UA') : 'Ще не виконувалось'}</Descriptions.Item>
            </Descriptions>
          </Card>

          {info.model_needs_retraining && (
            <Alert className="section-row" type="warning" showIcon message="Потрібне перенавчання моделей" description="Після зміни даних перейдіть до розділу «Моделі» та запустіть навчання." />
          )}

          {lastUpload && (
            <Alert className="section-row" type="success" showIcon message="Останнє завантаження завершено" description={`Збережено ${lastUpload.quality.saved_daily_rows} щоденних записів. Формат: ${lastUpload.quality.input_format === 'wide' ? 'широкий' : 'довгий'}.`} />
          )}

          <Card title="Останні записи" bordered={false} className="panel-card section-row">
            <Table<MultiDailyVisit>
              rowKey="date" dataSource={preview} pagination={false} size="small" scroll={{ x: 640 }}
              columns={[
                { title: 'Дата', dataIndex: 'date' },
                { title: 'МРТ', dataIndex: 'mri', align: 'right' },
                { title: 'КТ', dataIndex: 'ct', align: 'right' },
                { title: 'Рентген', dataIndex: 'xray', align: 'right' },
                { title: 'Усього', dataIndex: 'total', align: 'right' },
              ]}
            />
          </Card>
        </>
      )}
    </>
  )
}
