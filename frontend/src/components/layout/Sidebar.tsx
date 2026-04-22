import { NavLink, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard, MessageSquare, FileText, Bell,
  Upload, Settings, LogOut, Brain, ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/endpoints'
import toast from 'react-hot-toast'

const NAV_ITEMS = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard'    },
  { to: '/insights',   icon: Brain,           label: 'AI Insights'  },
  { to: '/reviews',    icon: FileText,        label: 'Reviews'      },
  { to: '/chat',       icon: MessageSquare,   label: 'Chat with AI' },
  { to: '/alerts',     icon: Bell,            label: 'Alerts'       },
  { to: '/upload',     icon: Upload,          label: 'Upload Data'  },
  { to: '/admin',      icon: Settings,        label: 'Admin'        },
]

export function Sidebar() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } finally {
      clearAuth()
      navigate('/login')
      toast.success('Logged out successfully')
    }
  }

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="fixed left-0 top-0 h-screen w-64 z-40 flex flex-col"
      style={{
        background: 'rgba(10, 10, 15, 0.95)',
        borderRight: '1px solid rgba(255,255,255,0.07)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Logo */}
      <div className="px-6 py-6 flex items-center gap-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #7c3aed, #2563eb)' }}
        >
          <Brain size={18} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-white leading-tight">SentimentAI</p>
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Multilingual</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}>
            {({ isActive }) => (
              <motion.div
                whileHover={{ x: 3 }}
                transition={{ duration: 0.15 }}
                className={cn('sidebar-item', isActive && 'active')}
              >
                <Icon size={16} />
                <span>{label}</span>
                {isActive && (
                  <ChevronRight size={14} className="ml-auto opacity-60" />
                )}
              </motion.div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div
        className="mx-3 mb-4 p-3 rounded-xl"
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #2563eb)' }}
          >
            {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-semibold text-white truncate">{user?.full_name}</p>
            <p className="text-xs capitalize" style={{ color: 'rgba(255,255,255,0.4)' }}>
              {user?.role}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all duration-200"
          style={{ color: 'rgba(255,255,255,0.45)' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = '#f87171'
            e.currentTarget.style.background = 'rgba(248,113,113,0.08)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'rgba(255,255,255,0.45)'
            e.currentTarget.style.background = 'transparent'
          }}
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </motion.aside>
  )
}
