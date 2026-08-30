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
  const maxReconnectDelay = 30000
  const pendingUpdatesRef = useRef({})

  const wsUrl = useMemo(() => {
    if (url) return url
    const base = import.meta.env?.VITE_WS_URL || 'ws://localhost:8000'
    return base.endsWith('/ws/vessels') ? base : `${base}/ws/vessels`
  }, [url])

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WS] Connected to', wsUrl)
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)

          // Backend broadcasts: { type: "position_update", data: { mmsi, latitude, longitude, ... } }
          if (msg.type === 'position_update' && msg.data) {
            const d = msg.data
            queuePositionUpdate(pendingUpdatesRef, d.mmsi || d.imo, d)
          }

          // Also support batch format: { type: "position_update", vessels: [...] }
          if (msg.type === 'position_update' && Array.isArray(msg.vessels)) {
            for (const v of msg.vessels) {
              queuePositionUpdate(pendingUpdatesRef, v.mmsi || v.imo, v)
            }
          }

          // Single update shorthand: { type: "single_update", mmsi, lat, lon, ... }
          if (msg.type === 'single_update') {
            queuePositionUpdate(pendingUpdatesRef, msg.mmsi || msg.imo, msg)
          }
        } catch {
          // Ignore malformed messages
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null

        // Auto-reconnect with exponential backoff
        const attempts = reconnectAttemptsRef.current
        const delay = Math.min(1000 * Math.pow(2, attempts), maxReconnectDelay)
        console.log(`[WS] Disconnected. Reconnecting in ${delay / 1000}s...`)
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current += 1
          connect()
        }, delay)
      }

      ws.onerror = () => {
        setError('WebSocket connection error')
        ws.close()
      }
    } catch (err) {
      setError(err.message)
    }
  }, [wsUrl])

  useEffect(() => {
    connect()
    return () => {
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
