import { useState, useEffect, useRef, useCallback, useMemo } from 'react'

const MAX_PENDING_UPDATES = 1500

function isFiniteCoordinate(value) {
  return Number.isFinite(Number(value))
}

function queuePositionUpdate(pendingUpdatesRef, keyValue, update) {
  const key = keyValue != null ? String(keyValue) : ''
  const lat = update.lat ?? update.latitude
  const lon = update.lon ?? update.longitude

  if (!key || key === 'undefined' || !isFiniteCoordinate(lat) || !isFiniteCoordinate(lon)) {
    return
  }

  pendingUpdatesRef.current[key] = {
    lat: Number(lat),
    lon: Number(lon),
    heading: update.heading,
    speed: update.speed,
    timestamp: update.timestamp || update.time || new Date().toISOString(),
  }
}

/**
 * WebSocket hook for live vessel position updates.
 *
 * Connects to the backend WebSocket at /ws/vessels and merges
 * incoming position updates into a positions map keyed by MMSI.
 *
 * The backend broadcasts messages in the format:
 *   { type: "position_update", data: { mmsi, latitude, longitude, speed, course, heading, ... } }
 */
export default function useWebSocket(url) {
  const [positions, setPositions] = useState({})
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const isUnmountedRef = useRef(false)
  const maxReconnectDelay = 30000
  const pendingUpdatesRef = useRef({})

  const wsUrl = useMemo(() => {
    if (url) return url
    if (import.meta.env?.VITE_WS_URL) {
      const base = import.meta.env.VITE_WS_URL
      return base.endsWith('/ws/vessels') ? base : `${base}/ws/vessels`
    }
    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:'
    const protocol = isHttps ? 'wss:' : 'ws:'
    const host = typeof window !== 'undefined'
      ? (window.location.port === '5173' ? `${window.location.hostname}:8000` : window.location.host)
      : 'localhost:8000'
    return `${protocol}//${host}/ws/vessels`
  }, [url])

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (isUnmountedRef.current) return
        console.log('[WS] Connected to', wsUrl)
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        if (isUnmountedRef.current) return
        try {
          const msg = JSON.parse(event.data)

          // Direct position update: { type: "position_update", data: { ... } }
          if (msg.type === 'position_update' && msg.data) {
            const key = msg.data.mmsi ?? msg.data.id
            queuePositionUpdate(pendingUpdatesRef, key, msg.data)
          }

          // Legacy batch format: { type: "position_batch", positions: [ ... ] }
          if (msg.type === 'position_batch' && Array.isArray(msg.positions)) {
            for (const pos of msg.positions) {
              const key = pos.mmsi ?? pos.id
              queuePositionUpdate(pendingUpdatesRef, key, pos)
            }
          }

          // Single position format: { mmsi, latitude, longitude, ... }
          if (msg.mmsi && (msg.latitude || msg.lat)) {
            queuePositionUpdate(pendingUpdatesRef, msg.mmsi, msg)
          }

          // Enriched vessel format: { id, position: { lat, lon }, ... }
          if (msg.id && msg.position) {
            queuePositionUpdate(pendingUpdatesRef, msg.id, {
              ...msg,
              lat: msg.position.lat,
              lon: msg.position.lon,
            })
          }
        } catch {
          // Ignore malformed messages
        }
      }

      ws.onclose = () => {
        if (isUnmountedRef.current) return
        setIsConnected(false)
        wsRef.current = null

        // Auto-reconnect with bounded exponential backoff
        const attempts = Math.min(reconnectAttemptsRef.current, 10)
        const delay = Math.min(1000 * Math.pow(2, attempts), maxReconnectDelay)
        console.log(`[WS] Disconnected. Reconnecting in ${delay / 1000}s...`)
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isUnmountedRef.current) return
          reconnectAttemptsRef.current += 1
          connect()
        }, delay)
      }

      ws.onerror = () => {
        if (isUnmountedRef.current) return
        setError('WebSocket connection error')
        ws.close()
      }
    } catch (err) {
      if (!isUnmountedRef.current) {
        setError(err.message)
      }
    }
  }, [wsUrl])

  useEffect(() => {
    isUnmountedRef.current = false
    connect()
    return () => {
      isUnmountedRef.current = true
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connect])

  // Flush accumulated live position updates to state every 2 seconds to prevent rendering lag.
  // IMPORTANT: merge into existing state (spread `prev`) instead of replacing it entirely.
  // A full replacement would silently drop every vessel that sent no update in the last 2 s,
  // causing markers to flicker off the map until the next batch they appear in.
  useEffect(() => {
    const interval = setInterval(() => {
      const pending = pendingUpdatesRef.current
      const entries = Object.entries(pending)
      if (entries.length === 0) return

      // When the batch is too large, keep only the most recent MAX_PENDING_UPDATES
      // entries. Copy the array before sorting to avoid mutating the original
      // entries reference in place — Array.prototype.sort() is destructive and
      // could produce subtle ordering bugs if entries is referenced elsewhere
      // in the same tick. Sort by proper Date comparison, not localeCompare,
      // which can produce incorrect ordering for ISO strings of different lengths.
      const cappedEntries =
        entries.length > MAX_PENDING_UPDATES
          ? [...entries]
              .sort(
                (a, b) =>
                  (Date.parse(b[1].timestamp) || 0) - (Date.parse(a[1].timestamp) || 0)
              )
              .slice(0, MAX_PENDING_UPDATES)
          : entries

      setPositions((prev) => ({
        ...prev,
        ...Object.fromEntries(cappedEntries),
      }))
      pendingUpdatesRef.current = {}
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return { positions, isConnected, error }
}
