import { Bell, MessageSquare, Activity } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDashboardStore } from '@/store/dashboardStore'
import { useQuery } from '@tanstack/react-query'
import { alertsApi } from '@/api/endpoints'
import { useNavigate } from 'react-router-dom'

interface TopBarProps {
  title: string
  subtitle?: string
}

export function TopBar({ title, subtitle }: TopBarProps) {
  const { toggleChat, liveNewReviews, resetLiveReviews } = useDashboardStore()
  const navigate = useNavigate()

  const { data: alertData } = useQuery({
    queryKey: ['alerts-count'],
    queryFn: () => alertsApi.list(false),
    refetchInterval: 60_000,
  })

  const unresolved = alertData?.unresolved_count ?? 0

  const handleNewReviewsClick = () => {
    resetLiveReviews()
    navigate('/dashboard')
  }

  return (
    <motion.header
      initial={{ y: -10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="h-16 flex items-center justify-between px-6 flex-shrink-0"
      style={{
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        background: 'rgba(10,10,15,0.6)',
        backdropFilter: 'blur(12px)',
      }}
    >
      {/* Page title */}
      <div>
        <h1 className="text-base font-semibold text-white">{title}</h1>
        {subtitle && (
          <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
            {subtitle}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">

        {/* Live new reviews badge */}
        <AnimatePresence>
          {liveNewReviews > 0 && (
            <motion.button
              key="live-badge"
              initial={{ opacity: 0, scale: 0.8, x: 10 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.8, x: 10 }}
              transition={{ duration: 0.2 }}
              onClick={handleNewReviewsClick}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold"
              style={{
                background: 'rgba(124,58,237,0.15)',
                border: '1px solid rgba(124,58,237,0.3)',
                color: '#a78bfa',
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ background: '#a78bfa', boxShadow: '0 0 6px #a78bfa' }}
              />
              <Activity size={12} />
              {liveNewReviews.toLocaleString()} new
            </motion.button>
          )}
        </AnimatePresence>

        {/* Chat button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={toggleChat}
          className="btn-primary text-xs px-3 py-2"
        >
          <MessageSquare size={14} />
          Chat with AI
        </motion.button>

        {/* Alerts bell */}
        <button
          className="relative p-2 rounded-xl transition-all duration-200"
          style={{
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
          onClick={() => navigate('/alerts')}
        >
          <Bell size={16} style={{ color: 'rgba(255,255,255,0.6)' }} />
          <AnimatePresence>
            {unresolved > 0 && (
              <motion.span
                key="alert-badge"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-xs flex items-center justify-center font-bold"
                style={{ background: '#f87171', fontSize: '9px' }}
              >
                {unresolved > 9 ? '9+' : unresolved}
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.header>
  )
}
