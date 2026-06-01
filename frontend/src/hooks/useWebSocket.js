import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * Custom hook for WebSocket connection to the vessel position stream.
 * Auto-reconnects with exponential backoff.
 */
export default function useWebSocket(url) {
  const [positions, setPositions] = useState({})
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimerRef = useRef(null)
  const maxReconnectDelay = 30000

  const connect = useCallback(() => {
    const wsUrl = url || import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/vessels'

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WS] Connected to vessel stream')
        setIsConnected(true)
        setError(null)
        reconnectAttemptRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'position_update' && data.vessels) {
            setPositions((prev) => {
              const updated = { ...prev }
              data.vessels.forEach((v) => {
                updated[v.mmsi || v.imo] = {
                  lat: v.lat,
                  lon: v.lon,
                  heading: v.heading,
                  speed: v.speed,
                  timestamp: v.timestamp,
                }
              })
              return updated
            })
          } else if (data.type === 'single_update') {
            setPositions((prev) => ({
              ...prev,
              [data.mmsi || data.imo]: {
                lat: data.lat,
                lon: data.lon,
                heading: data.heading,
                speed: data.speed,
                timestamp: data.timestamp,
              },
            }))
          }
        } catch (e) {
          console.warn('[WS] Failed to parse message:', e)
        }
      }

      ws.onerror = (event) => {
        console.error('[WS] Error:', event)
        setError('WebSocket connection error')
      }

      ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason)
        setIsConnected(false)
        wsRef.current = null

        // Exponential backoff reconnect
        const attempt = reconnectAttemptRef.current++
        const delay = Math.min(1000 * Math.pow(2, attempt), maxReconnectDelay)
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${attempt + 1})`)

        reconnectTimerRef.current = setTimeout(connect, delay)
      }
    } catch (e) {
      console.error('[WS] Failed to create WebSocket:', e)
      setError('Failed to connect to vessel stream')
    }
  }, [url])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting')
      }
    }
  }, [connect])

  return { positions, isConnected, error }
}
