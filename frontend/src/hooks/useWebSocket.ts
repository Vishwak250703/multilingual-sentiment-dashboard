import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'

type WSMessage = {
  event: string
  [key: string]: unknown
}

/**
 * Connects to the backend WebSocket for real-time events.
 * Auto-reconnects on disconnect. Sends heartbeat pings every 30s.
 */
export function useWebSocket(onMessage: (msg: WSMessage) => void) {
  const { user } = useAuthStore()
  const wsRef = useRef<WebSocket | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (!user?.tenant_id) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const url = `${protocol}://${host}/ws/${user.tenant_id}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        onMessageRef.current(data)
      } catch { /* ignore malformed */ }
    }

    ws.onopen = () => {
      // Start heartbeat
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 30_000)
    }

    ws.onclose = () => {
      if (pingRef.current) clearInterval(pingRef.current)
      // Reconnect after 3s
      reconnectRef.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => ws.close()
  }, [user?.tenant_id])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
      if (pingRef.current) clearInterval(pingRef.current)
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
    }
  }, [connect])
}
