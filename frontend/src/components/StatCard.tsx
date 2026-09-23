import type { ReactNode } from 'react'
import { Card, Statistic } from 'antd'

interface StatCardProps {
  title: string
  value: number | string
  precision?: number
  suffix?: ReactNode
  prefix?: ReactNode
}

export default function StatCard({ title, value, precision, suffix, prefix }: StatCardProps) {
  return (
    <Card className="stat-card" bordered={false}>
      <Statistic
        title={title}
        value={value}
        precision={precision}
        suffix={suffix}
        prefix={prefix}
      />
    </Card>
  )
}
