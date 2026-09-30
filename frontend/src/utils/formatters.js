export function parseTimestamp(val) {
  if (val == null || val === '') return null
  if (typeof val === 'number') {
    return val < 1e11 ? val * 1000 : val
  }
  if (typeof val === 'string' && !isNaN(val) && !isNaN(parseFloat(val))) {
    const num = Number(val)
    return num < 1e11 ? num * 1000 : num
  }
  const parsed = Date.parse(val)
  return isNaN(parsed) ? null : parsed
}

export function formatLastSeen(lastSeen) {
  if (!lastSeen) return '—'
  const timestamp = parseTimestamp(lastSeen)
  if (!timestamp || isNaN(timestamp)) return '—'
  const diff = Date.now() - timestamp
  if (diff < 0) return 'Just now'
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function formatEta(eta) {
  if (!eta) return '—'
  const timestamp = parseTimestamp(eta)
  if (!timestamp || isNaN(timestamp)) return '—'
  try {
    const d = new Date(timestamp)
    if (isNaN(d.getTime())) return '—'
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '—'
  }
}

export function formatPortDate(dateStr) {
  if (!dateStr) return '—'
  const timestamp = parseTimestamp(dateStr)
  if (!timestamp || isNaN(timestamp)) return '—'
  try {
    const d = new Date(timestamp)
    if (isNaN(d.getTime())) return '—'
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return '—'
  }
}
