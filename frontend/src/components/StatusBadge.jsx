import styles from './StatusBadge.module.css'

const statusLabels = {
  draft: 'Draft',
  active: 'Active',
  archived: 'Archived',
  published: 'Published',
  retired: 'Retired',
}

function StatusBadge({ status }) {
  return (
    <span className={`${styles.badge} ${styles[status]}`}>
      {statusLabels[status] || status}
    </span>
  )
}

export default StatusBadge
