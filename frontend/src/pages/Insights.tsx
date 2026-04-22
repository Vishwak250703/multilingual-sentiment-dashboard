import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Info, AlertTriangle, Zap, TrendingUp, Layers, Hash, RefreshCw,
} from 'lucide-react'

import { TopBar } from '@/components/layout/TopBar'
import { insightsApi } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'
import type { InsightItem, AspectSentiment } from '@/types'

// ─── Constants ────────────────────────────────────────────────────────────────
const PERIODS = ['1d', '7d', '30d', '90d'] as const

const SEVERITY_CONFIG = {
  critical: {
    bg: 'rgba(239,68,68,0.1)',
    border: 'rgba(239,68,68,0.25)',
    icon: '#ef4444',
    label: 'Critical',
    IconC: Zap,
  },
  warning: {
    bg: 'rgba(245,158,11,0.1)',
    border: 'rgba(245,158,11,0.25)',
    icon: '#f59e0b',
    label: 'Warning',
    IconC: AlertTriangle,
  },
  info: {
    bg: 'rgba(37,99,235,0.1)',
    border: 'rgba(37,99,235,0.25)',
    icon: '#3b82f6',
    label: 'Info',
    IconC: Info,
  },
}

const TYPE_ICONS: Record<InsightItem['type'], React.ElementType> = {
  trend: TrendingUp,
  spike: Zap,
  keyword: Hash,
  aspect: Layers,
}

// ─── Period Filter ────────────────────────────────────────────────────────────
function PeriodFilter({ value, onChange }: { value: string; onChange: (p: string) => void }) {
  return (
    <div
      className="flex gap-1 p-1 rounded-xl"
      style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
    >
      {PERIODS.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
          style={
            value === p
              ? { background: 'linear-gradient(135deg,#7c3aed,#2563eb)', color: '#fff' }
              : { color: 'rgba(255,255,255,0.45)' }
          }
        >
          {p}
        </button>
      ))}
    </div>
  )
}

// ─── Insight Card ─────────────────────────────────────────────────────────────
function InsightCard({ item, index }: { item: InsightItem; index: number }) {
  const cfg = SEVERITY_CONFIG[item.severity] ?? SEVERITY_CONFIG.info
  const TypeIcon = TYPE_ICONS[item.type] ?? Info

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="flex gap-4 p-4 rounded-2xl"
      style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}
    >
      {/* Severity icon column */}
      <div className="flex flex-col items-center gap-2 flex-shrink-0 pt-0.5">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: `${cfg.icon}22` }}
        >
          <cfg.IconC size={16} style={{ color: cfg.icon }} />
        </div>
        <span
          className="text-[10px] font-semibold uppercase tracking-wider"
          style={{ color: cfg.icon }}
        >
          {cfg.label}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1.5">
          <TypeIcon size={11} style={{ color: 'rgba(255,255,255,0.35)' }} />
          <span
            className="text-[10px] uppercase tracking-wider"
            style={{ color: 'rgba(255,255,255,0.35)' }}
          >
            {item.type}
          </span>
        </div>
        <p className="text-sm font-semibold text-white mb-1.5">{item.title}</p>
        <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
          {item.description}
        </p>
      </div>
    </motion.div>
  )
}

// ─── Aspect Score Row ─────────────────────────────────────────────────────────
function AspectRow({
  item,
  index,
  maxCount,
}: {
  item: AspectSentiment
  index: number
  maxCount: number
}) {
  const barColor =
    item.score >= 0.1 ? '#10b981' : item.score <= -0.1 ? '#f87171' : '#94a3b8'
  const countBarWidth = maxCount > 0 ? (item.count / maxCount) * 100 : 0

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
      className="grid items-center gap-4"
      style={{ gridTemplateColumns: '140px 1fr 72px 72px' }}
    >
      {/* Aspect name */}
      <p className="text-xs font-medium capitalize truncate" style={{ color: 'rgba(255,255,255,0.8)' }}>
        {item.aspect}
      </p>

      {/* Centered score bar */}
      <div
        className="relative h-2 rounded-full"
        style={{ background: 'rgba(255,255,255,0.07)' }}
      >
        {/* Filled segment */}
        <div
          className="absolute top-0 h-full rounded-full transition-all duration-700"
          style={
            item.score >= 0
              ? {
                  left: '50%',
                  width: `${item.score * 50}%`,
                  background: barColor,
                  boxShadow: `0 0 5px ${barColor}66`,
                }
              : {
                  right: '50%',
                  width: `${Math.abs(item.score) * 50}%`,
                  background: barColor,
                  boxShadow: `0 0 5px ${barColor}66`,
                }
          }
        />
        {/* Center divider */}
        <div
          className="absolute top-0 left-1/2 w-px h-full"
          style={{ background: 'rgba(255,255,255,0.22)' }}
        />
      </div>

      {/* Score value */}
      <p className="text-xs font-semibold text-right" style={{ color: barColor }}>
        {item.score >= 0 ? '+' : ''}
        {item.score.toFixed(3)}
      </p>

      {/* Frequency mini-bar + count */}
      <div className="flex items-center gap-2">
        <div
          className="flex-1 h-1.5 rounded-full overflow-hidden"
          style={{ background: 'rgba(255,255,255,0.06)' }}
        >
          <div
            className="h-full rounded-full"
            style={{
              width: `${countBarWidth}%`,
              background: 'rgba(167,139,250,0.5)',
            }}
          />
        </div>
        <span className="text-[10px] flex-shrink-0" style={{ color: 'rgba(255,255,255,0.35)' }}>
          {item.count}
        </span>
      </div>
    </motion.div>
  )
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────
function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-20 rounded-2xl animate-pulse"
          style={{ background: 'rgba(255,255,255,0.04)' }}
        />
      ))}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Insights() {
  const { filters, setFilters } = useDashboardStore()
  const period = filters.period

  const {
    data: insights = [],
    isLoading: insightsLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['insights', period],
    queryFn: () => insightsApi.getInsights(period),
    staleTime: 30_000,
    refetchInterval: 120_000,
  })

  const { data: aspects = [], isLoading: aspectsLoading } = useQuery({
    queryKey: ['insights-aspects', period],
    queryFn: () => insightsApi.getAspects(period),
    staleTime: 30_000,
  })

  // Sort insights: critical → warning → info
  const sortedInsights = useMemo(() => {
    const order: Record<string, number> = { critical: 0, warning: 1, info: 2 }
    return [...insights].sort(
      (a, b) => (order[a.severity] ?? 2) - (order[b.severity] ?? 2)
    )
  }, [insights])

  // Sort aspects by count (most-mentioned first)
  const sortedAspects = useMemo(
    () => [...aspects].sort((a, b) => b.count - a.count),
    [aspects]
  )

  const maxCount = useMemo(
    () => Math.max(...aspects.map((a) => a.count), 1),
    [aspects]
  )

  const criticalCount = insights.filter((i) => i.severity === 'critical').length
  const warningCount = insights.filter((i) => i.severity === 'warning').length

  return (
    <div className="flex flex-col h-full">
      <TopBar title="AI Insights" subtitle="Automated analysis and recommendations" />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* ── Header row ─────────────────────────────────────────── */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap">
            <PeriodFilter
              value={period}
              onChange={(p) => setFilters({ period: p as typeof period })}
            />

            {/* Severity summary badges */}
            {!insightsLoading && (criticalCount > 0 || warningCount > 0) && (
              <div className="flex items-center gap-2">
                {criticalCount > 0 && (
                  <span
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold"
                    style={{
                      background: 'rgba(239,68,68,0.15)',
                      color: '#f87171',
                      border: '1px solid rgba(239,68,68,0.25)',
                    }}
                  >
                    <Zap size={10} />
                    {criticalCount} critical
                  </span>
                )}
                {warningCount > 0 && (
                  <span
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold"
                    style={{
                      background: 'rgba(245,158,11,0.12)',
                      color: '#fbbf24',
                      border: '1px solid rgba(245,158,11,0.25)',
                    }}
                  >
                    <AlertTriangle size={10} />
                    {warningCount} warnings
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Regenerate button */}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200"
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: isFetching ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.5)',
              cursor: isFetching ? 'not-allowed' : 'pointer',
            }}
          >
            <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
            Regenerate
          </button>
        </div>

        {/* ── AI Insights section ─────────────────────────────────── */}
        <div className="glass-card p-5">
          <div className="flex items-center gap-2.5 mb-5">
            <div
              className="w-7 h-7 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(124,58,237,0.2)' }}
            >
              <Zap size={14} className="text-brand-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">AI-Generated Insights</p>
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                Powered by Claude · Based on last {period}
              </p>
            </div>
          </div>

          {insightsLoading ? (
            <Skeleton rows={3} />
          ) : sortedInsights.length === 0 ? (
            <div className="py-14 text-center">
              <div
                className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                style={{ background: 'rgba(255,255,255,0.05)' }}
              >
                <Zap size={20} style={{ color: 'rgba(255,255,255,0.2)' }} />
              </div>
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
                Upload reviews to generate AI insights
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {sortedInsights.map((item, i) => (
                <InsightCard key={i} item={item} index={i} />
              ))}
            </div>
          )}
        </div>

        {/* ── Aspect Sentiment section ────────────────────────────── */}
        <div className="glass-card p-5">
          <div className="flex items-center gap-2.5 mb-2">
            <div
              className="w-7 h-7 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(6,182,212,0.15)' }}
            >
              <Layers size={14} style={{ color: '#06b6d4' }} />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Aspect Sentiment Analysis</p>
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                Sentiment score per business aspect (−1 = very negative · +1 = very positive)
              </p>
            </div>
          </div>

          {/* Legend row */}
          <div className="flex items-center gap-5 mt-3 mb-5 px-1">
            {[
              { color: '#f87171', label: 'Negative' },
              { color: '#10b981', label: 'Positive' },
              { color: '#94a3b8', label: 'Neutral' },
            ].map(({ color, label }) => (
              <div
                key={label}
                className="flex items-center gap-1.5 text-xs"
                style={{ color: 'rgba(255,255,255,0.4)' }}
              >
                <div
                  className="w-3 h-1.5 rounded-full"
                  style={{ background: color }}
                />
                {label}
              </div>
            ))}
            <div className="ml-auto text-[10px]" style={{ color: 'rgba(255,255,255,0.25)' }}>
              Freq →
            </div>
          </div>

          {/* Column headers */}
          <div
            className="grid items-center gap-4 mb-3 px-1"
            style={{ gridTemplateColumns: '140px 1fr 72px 72px' }}
          >
            {[
              { label: 'Aspect', align: 'left' },
              { label: 'Score', align: 'center' },
              { label: 'Value', align: 'right' },
              { label: 'Freq', align: 'left' },
            ].map(({ label, align }) => (
              <p
                key={label}
                className={`text-[10px] uppercase tracking-wider text-${align}`}
                style={{ color: 'rgba(255,255,255,0.28)' }}
              >
                {label}
              </p>
            ))}
          </div>

          {aspectsLoading ? (
            <Skeleton rows={5} />
          ) : sortedAspects.length === 0 ? (
            <div className="py-10 text-center">
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
                No aspect data for this period. Upload reviews with aspect-rich content.
              </p>
            </div>
          ) : (
            <div className="space-y-3.5 px-1">
              {sortedAspects.map((item, i) => (
                <AspectRow
                  key={item.aspect}
                  item={item}
                  index={i}
                  maxCount={maxCount}
                />
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
