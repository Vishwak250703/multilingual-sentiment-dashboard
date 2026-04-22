import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow, format } from 'date-fns'
import {
  TrendingDown, AlertTriangle, Package, GitBranch,
  Zap, CheckCircle2, BellOff, RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { TopBar } from '@/components/layout/TopBar'
import { alertsApi } from '@/api/endpoints'
import type { Alert, AlertSeverity, AlertType } from '@/types'

// ─── Severity styles ───────────────────────────────────────────
function severityStyle(severity: AlertSeverity) {
  switch (severity) {
    case 'critical': return { color: '#f87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)' }
    case 'high':     return { color: '#fb923c', bg: 'rgba(251,146,60,0.12)',  border: 'rgba(251,146,60,0.3)'  }
    case 'medium':   return { color: '#fbbf24', bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.3)'  }
    default:         return { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)', border: 'rgba(96,165,250,0.3)'  }
  }
}

// ─── Alert type icon & label ───────────────────────────────────
function alertTypeIcon(type: AlertType) {
  switch (type) {
    case 'sentiment_drop':  return TrendingDown
    case 'complaint_spike': return AlertTriangle
    case 'product_alert':   return Package
    case 'branch_alert':    return GitBranch
    default:                return Zap
  }
}

function alertTypeLabel(type: AlertType) {
  switch (type) {
    case 'sentiment_drop':  return 'Sentiment Drop'
    case 'complaint_spike': return 'Complaint Spike'
    case 'product_alert':   return 'Product Alert'
    case 'branch_alert':    return 'Branch Alert'
    default:                return 'Anomaly'
  }
}

function formatRelative(dt: string) {
  try { return formatDistanceToNow(new Date(dt), { addSuffix: true }) } catch { return '—' }
}

function formatExact(dt: string) {
  try { return format(new Date(dt), 'MMM d, yyyy HH:mm') } catch { return '—' }
}

// ─── Alert Card ────────────────────────────────────────────────
function AlertCard({
  alert,
  onResolve,
  resolving,
}: {
  alert: Alert
  onResolve: (id: string) => void
  resolving: boolean
}) {
  const sv = severityStyle(alert.severity)
  const Icon = alertTypeIcon(alert.alert_type)
  const meta = alert.metadata ?? {}

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.2 }}
      className="glass-card p-5"
      style={{ opacity: alert.is_resolved ? 0.65 : 1 }}
    >
      <div className="flex items-start gap-4">
        {/* Severity icon */}
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{ background: sv.bg, border: `1px solid ${sv.border}` }}
        >
          <Icon size={18} style={{ color: sv.color }} />
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              {/* Badges */}
              <div className="flex items-center flex-wrap gap-2 mb-1.5">
                <span
                  className="px-2 py-0.5 rounded-full text-xs font-bold capitalize"
                  style={{ background: sv.bg, color: sv.color, border: `1px solid ${sv.border}` }}
                >
                  {alert.severity}
                </span>
                <span
                  className="px-2 py-0.5 rounded-full text-xs capitalize"
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    color: 'rgba(255,255,255,0.5)',
                    border: '1px solid rgba(255,255,255,0.1)',
                  }}
                >
                  {alertTypeLabel(alert.alert_type)}
                </span>
                {alert.is_resolved && (
                  <span
                    className="px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      background: 'rgba(74,222,128,0.1)',
                      color: '#4ade80',
                      border: '1px solid rgba(74,222,128,0.2)',
                    }}
                  >
                    Resolved
                  </span>
                )}
              </div>

              {/* Title */}
              <h3 className="text-sm font-semibold text-white mb-1">{alert.title}</h3>

              {/* Message */}
              <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
                {alert.message}
              </p>

              {/* Metadata details */}
              {Object.keys(meta).length > 0 && (
                <div
                  className="flex flex-wrap gap-4 mt-3 px-3 py-2 rounded-xl"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                >
                  {Object.entries(meta).map(([k, v]) => v != null && (
                    <div key={k} className="flex items-center gap-1">
                      <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
                        {k.replace(/_/g, ' ')}:
                      </span>
                      <span className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.7)' }}>
                        {typeof v === 'number' ? v.toLocaleString() : String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Timestamps */}
              <div className="flex items-center gap-2 mt-3 flex-wrap">
                <span
                  className="text-xs"
                  style={{ color: 'rgba(255,255,255,0.3)' }}
                  title={formatExact(alert.triggered_at)}
                >
                  Triggered {formatRelative(alert.triggered_at)}
                </span>
                {alert.is_resolved && alert.resolved_at && (
                  <>
                    <span style={{ color: 'rgba(255,255,255,0.15)' }}>·</span>
                    <span
                      className="text-xs"
                      style={{ color: 'rgba(255,255,255,0.25)' }}
                      title={formatExact(alert.resolved_at)}
                    >
                      Resolved {formatRelative(alert.resolved_at)}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Resolve button */}
            {!alert.is_resolved && (
              <button
                onClick={() => onResolve(alert.id)}
                disabled={resolving}
                className="btn-ghost text-xs px-3 py-1.5 flex-shrink-0"
                style={{
                  borderColor: 'rgba(74,222,128,0.25)',
                  color: '#4ade80',
                  background: 'rgba(74,222,128,0.06)',
                }}
              >
                {resolving ? (
                  <span className="w-3 h-3 rounded-full border border-green-400/60 border-t-transparent animate-spin" />
                ) : (
                  <CheckCircle2 size={13} />
                )}
                Resolve
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── Stat Card ─────────────────────────────────────────────────
function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="glass-card p-4">
      <p className="text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>
        {label}
      </p>
      <p className="text-2xl font-bold" style={{ color }}>
        {value}
      </p>
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────
export default function Alerts() {
  const [tab, setTab] = useState<'active' | 'all'>('active')
  const [resolvingId, setResolvingId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['alerts', tab],
    queryFn: () => alertsApi.list(tab === 'all'),
    refetchInterval: 30_000,
  })

  const resolve = useMutation({
    mutationFn: (id: string) => alertsApi.resolve(id),
    onMutate: (id) => setResolvingId(id),
    onSuccess: () => {
      toast.success('Alert resolved')
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alerts-count'] })
    },
    onError: () => toast.error('Failed to resolve alert'),
    onSettled: () => setResolvingId(null),
  })

  const items = data?.items ?? []
  const unresolved = data?.unresolved_count ?? 0
  const total = data?.total ?? 0
  const resolved = total - unresolved

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Alerts" subtitle="Monitoring and anomaly detection" />

      <div className="flex-1 overflow-y-auto p-6 space-y-4">

        {/* ── Stats Row ──────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-4">
          <StatCard
            label="Active Alerts"
            value={unresolved}
            color={unresolved > 0 ? '#f87171' : '#4ade80'}
          />
          <StatCard label="Total Alerts" value={total} color="rgba(255,255,255,0.9)" />
          <StatCard label="Resolved" value={resolved} color="#4ade80" />
        </div>

        {/* ── Tabs + Refresh ─────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div
            className="flex gap-1 p-1 rounded-xl"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            {(['active', 'all'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
                style={
                  tab === t
                    ? { background: 'linear-gradient(135deg,#7c3aed,#2563eb)', color: '#fff' }
                    : { color: 'rgba(255,255,255,0.45)' }
                }
              >
                {t === 'active' ? `Active (${unresolved})` : `All (${total})`}
              </button>
            ))}
          </div>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="btn-ghost text-xs px-3 py-2"
          >
            <RefreshCw size={13} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* ── Alert List ─────────────────────────────────────────── */}
        {isError ? (
          <div className="glass-card p-8 flex flex-col items-center gap-3">
            <AlertTriangle size={24} style={{ color: '#f87171' }} />
            <p className="text-sm text-red-400">Failed to load alerts</p>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-12 flex flex-col items-center gap-4"
          >
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.15)' }}
            >
              <BellOff size={24} style={{ color: '#4ade80' }} />
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-white mb-1">
                {tab === 'active' ? 'No active alerts' : 'No alerts yet'}
              </p>
              <p
                className="text-xs leading-relaxed"
                style={{ color: 'rgba(255,255,255,0.35)', maxWidth: '300px' }}
              >
                {tab === 'active'
                  ? 'The system is running normally. Alerts will appear here when sentiment drops or complaint spikes are detected.'
                  : 'No alerts have been generated yet. The alert checker runs every 5 minutes.'}
              </p>
            </div>
          </motion.div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence mode="popLayout">
              {items.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onResolve={(id) => resolve.mutate(id)}
                  resolving={resolvingId === alert.id && resolve.isPending}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
