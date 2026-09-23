import { Select } from 'antd'
import type { Modality } from '../types/api'

export const modalityOptions = [
  { value: 'all', label: 'Усі обстеження' },
  { value: 'mri', label: 'МРТ' },
  { value: 'ct', label: 'КТ' },
  { value: 'xray', label: 'Рентген' },
]

export default function ModalitySelect({ value, onChange }: { value: Modality; onChange: (value: Modality) => void }) {
  return <Select value={value} onChange={onChange} options={modalityOptions} style={{ minWidth: 190 }} />
}
