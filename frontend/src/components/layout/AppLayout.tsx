import { useCallback } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

import { Sidebar } from './Sidebar'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useDashboardStore } from '@/store/dashboardStore'

export function AppLayout() {
  const location = useLocation()
  const queryClient = useQueryClient()
  const { incrementLiveReviews } = useDashboardStore()

  const handleWsMessage = useCallback((msg: { event: string; [key: string]: unknown }) => {
    switch (msg.event) {
      case 'new_review':
        incrementLiveReviews(1)
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
        queryClient.invalidateQueries({ queryKey: ['reviews'] })
        break

      case 'job_complete': {
        const processed = typeof msg.processed === 'number' ? msg.processed : 0
        if (processed > 0) incrementLiveReviews(processed)
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
        queryClient.invalidateQueries({ queryKey: ['reviews'] })
        break
      }

      case 'new_alert':
        queryClient.invalidateQueries({ queryKey: ['alerts'] })
        queryClient.invalidateQueries({ queryKey: ['alerts-count'] })
        toast('New alert detected', {
          icon: '🔔',
          style: {
            background: 'rgba(20,20,43,0.95)',
            color: '#fff',
            border: '1px solid rgba(248,113,113,0.3)',
          },
        })
        break

      case 'dashboard_update':
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
        break

      default:
        break
    }
  }, [queryClient, incrementLiveReviews])

  useWebSocket(handleWsMessage)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      {/* Main content area */}
      <main className="flex-1 flex flex-col overflow-hidden" style={{ marginLeft: '256px' }}>
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}
