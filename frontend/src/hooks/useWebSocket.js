import { useState, useEffect, useRef, useCallback } from 'react'

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

  const wsUrl =
    url ||
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_WS_URL
      ? (import.meta.env.VITE_WS_URL.endsWith('/ws/vessels')
          ? import.meta.env.VITE_WS_URL
          : `${import.meta.env.VITE_WS_URL}/ws/vessels`)
      : 'ws://localhost:8000/ws/vessels')

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
            const key = String(d.mmsi || d.imo)
            setPositions((prev) => ({
              ...prev,
              [key]: {
                lat: d.latitude,
                lon: d.longitude,
                heading: d.heading,
                speed: d.speed,
                timestamp: d.time || new Date().toISOString(),
              },
            }))
          }

          // Also support batch format: { type: "position_update", vessels: [...] }
          if (msg.type === 'position_update' && Array.isArray(msg.vessels)) {
            setPositions((prev) => {
              const next = { ...prev }
              for (const v of msg.vessels) {
                const key = String(v.mmsi || v.imo)
                next[key] = {
                  lat: v.lat ?? v.latitude,
                  lon: v.lon ?? v.longitude,
                  heading: v.heading,
                  speed: v.speed,
                  timestamp: v.timestamp || v.time || new Date().toISOString(),
                }
              }
              return next
            })
          }

          // Single update shorthand: { type: "single_update", mmsi, lat, lon, ... }
          if (msg.type === 'single_update') {
            const key = String(msg.mmsi || msg.imo)
            setPositions((prev) => ({
              ...prev,
              [key]: {
                lat: msg.lat ?? msg.latitude,
                lon: msg.lon ?? msg.longitude,
                heading: msg.heading,
                speed: msg.speed,
                timestamp: msg.timestamp || new Date().toISOString(),
              },
            }))
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

      ws.onerror = (e) => {
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

  return { positions, isConnected, error }
}
