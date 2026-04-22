import { useEffect, useRef, useMemo } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts'
import {
  TrendingUp, TrendingDown, Minus, Globe, MessageSquare,
  Zap, AlertTriangle, Info, Hash,
} from 'lucide-react'

import { TopBar } from '@/components/layout/TopBar'
import { ChatPanel } from '@/components/dashboard/ChatPanel'
import { dashboardApi, insightsApi } from '@/api/endpoints'
import { useDashboardStore } from '@/store/dashboardStore'
import type { KPIData, InsightItem, AspectSentiment } from '@/types'

// ─── Animated Counter ─────────────────────────────────────────────────────────
function useCountUp(target: number, duration = 900) {
  const ref = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const start = performance.now()
    const from = 0
    const animate = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3)
      const current = from + (target - from) * ease
      if (ref.current) ref.current.textContent = Number.isInteger(target)
        ? Math.round(current).toLocaleString()
        : current.toFixed(1)
      if (progress < 1) requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)
  }, [target, duration])
  return ref
}

// ─── Sentiment Emoji Face ─────────────────────────────────────────────────────
function SentimentFace({ score }: { score: number }) {
  if (score >= 0.3) return <span className="text-4xl">😊</span>
  if (score >= 0.05) return <span className="text-4xl">🙂</span>
  if (score >= -0.05) return <span className="text-4xl">😐</span>
  if (score >= -0.3) return <span className="text-4xl">😕</span>
  return <span className="text-4xl">😟</span>
}

// ─── KPI Card ────────────────────────────────────────────────────────────────
function KPICard({
  label, value, suffix = '', icon: Icon, color, delta,
}: {
  label: string
  value: number
  suffix?: string
  icon: React.ElementType
  color: string
  delta?: number
}) {
  const ref = useCountUp(value)
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-card p-5 flex flex-col gap-3"
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.45)' }}>
          {label}
        </p>
        <div
          className="w-8 h-8 rounded-xl flex items-center justify-center"
          style={{ background: `${color}22` }}
        >
          <Icon size={15} style={{ color }} />
        </div>
      </div>
      <div className="flex items-end gap-2">
        <p className="text-2xl font-bold text-white">
          <span ref={ref}>0</span>
          {suffix && <span className="text-base text-white/50 ml-0.5">{suffix}</span>}
        </p>
        {delta !== undefined && (
          <div className={`flex items-center gap-0.5 text-xs mb-0.5 ${delta > 0 ? 'text-neon-green' : delta < 0 ? 'text-red-400' : 'text-white/40'}`}>
            {delta > 0 ? <TrendingUp size={12} /> : delta < 0 ? <TrendingDown size={12} /> : <Minus size={12} />}
            <span>{Math.abs(delta).toFixed(2)}</span>
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Period Filter ─────────────────────────────────────────────────────────────
const PERIODS = ['1d', '7d', '30d', '90d'] as const
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

// ─── Sentiment Trend Chart ─────────────────────────────────────────────────────
function TrendChart({ points }: { points: Array<{ date: string; sentiment_score: number; positive_count: number; negative_count: number; total: number }> }) {
  if (!points.length) return <EmptyChart label="No trend data yet" />

  const formatDate = (d: string) => {
    const date = new Date(d)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div
        className="rounded-xl p-3 text-xs"
        style={{ background: 'rgba(15,15,25,0.95)', border: '1px solid rgba(124,58,237,0.3)', backdropFilter: 'blur(12px)' }}
      >
        <p className="text-white/60 mb-2">{formatDate(label)}</p>
        <p className="text-white font-semibold">Score: <span className="text-brand-300">{d.sentiment_score.toFixed(2)}</span></p>
        <p className="text-neon-green">Positive: {d.positive_count}</p>
        <p className="text-red-400">Negative: {d.negative_count}</p>
        <p className="text-white/50">Total: {d.total}</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={points} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
        <defs>
          <linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[-1, 1]}
          tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="sentiment_score"
          stroke="url(#scoreGrad)"
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 5, fill: '#7c3aed', stroke: 'rgba(124,58,237,0.3)', strokeWidth: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ─── Language Donut ───────────────────────────────────────────────────────────
const LANG_COLORS = ['#7c3aed', '#2563eb', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

function LanguageDonut({ data }: { data: Array<{ language: string; language_name: string; count: number; percent: number }> }) {
  if (!data.length) return <EmptyChart label="No language data yet" />

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div
        className="rounded-xl p-3 text-xs"
        style={{ background: 'rgba(15,15,25,0.95)', border: '1px solid rgba(124,58,237,0.3)', backdropFilter: 'blur(12px)' }}
      >
        <p className="text-white font-semibold">{d.language_name}</p>
        <p className="text-white/60">{d.count} reviews · {d.percent}%</p>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4">
      <ResponsiveContainer width={160} height={160}>
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="language_name"
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={72}
            paddingAngle={2}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={LANG_COLORS[i % LANG_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex-1 space-y-2">
        {data.slice(0, 6).map((item, i) => (
          <div key={item.language} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: LANG_COLORS[i % LANG_COLORS.length] }} />
              <span className="text-xs text-white/70">{item.language_name}</span>
            </div>
            <span className="text-xs font-medium text-white/50">{item.percent}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Source Bar Chart ─────────────────────────────────────────────────────────
function SourceBar({ data }: { data: Array<{ source: string; count: number; sentiment_score: number }> }) {
  if (!data.length) return <EmptyChart label="No source data yet" />

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div
        className="rounded-xl p-3 text-xs"
        style={{ background: 'rgba(15,15,25,0.95)', border: '1px solid rgba(124,58,237,0.3)', backdropFilter: 'blur(12px)' }}
      >
        <p className="text-white font-semibold capitalize">{d.source}</p>
        <p className="text-white/60">{d.count} reviews</p>
        <p className={d.sentiment_score >= 0 ? 'text-neon-green' : 'text-red-400'}>
          Avg score: {d.sentiment_score.toFixed(2)}
        </p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.8} />
            <stop offset="100%" stopColor="#2563eb" stopOpacity={0.8} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
        <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis
          type="category"
          dataKey="source"
          tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={60}
          tickFormatter={(v: string) => v.charAt(0).toUpperCase() + v.slice(1)}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" fill="url(#barGrad)" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Empty State ──────────────────────────────────────────────────────────────
function EmptyChart({ label }: { label: string }) {
  return (
    <div className="h-40 flex flex-col items-center justify-center gap-2">
      <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.05)' }}>
        <TrendingUp size={16} style={{ color: 'rgba(255,255,255,0.2)' }} />
      </div>
      <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>{label}</p>
    </div>
  )
}

// ─── Insight Card ─────────────────────────────────────────────────────────────
function InsightCard({ item }: { item: InsightItem }) {
  const colors = {
    info: { bg: 'rgba(37,99,235,0.1)', border: 'rgba(37,99,235,0.25)', icon: '#3b82f6', IconC: Info },
    warning: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.25)', icon: '#f59e0b', IconC: AlertTriangle },
    critical: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.25)', icon: '#ef4444', IconC: Zap },
  }
  const c = colors[item.severity] ?? colors.info
  const { IconC } = c

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex gap-3 p-3 rounded-xl"
      style={{ background: c.bg, border: `1px solid ${c.border}` }}
    >
      <div className="mt-0.5 flex-shrink-0">
        <IconC size={14} style={{ color: c.icon }} />
      </div>
      <div>
        <p className="text-xs font-semibold text-white mb-0.5">{item.title}</p>
        <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>{item.description}</p>
      </div>
    </motion.div>
  )
}

// ─── Aspect Badge ─────────────────────────────────────────────────────────────
function AspectBadge({ item }: { item: AspectSentiment }) {
  const cls = item.sentiment === 'positive' ? 'badge-positive' : item.sentiment === 'negative' ? 'badge-negative' : 'badge-neutral'
  return (
    <span className={`${cls} capitalize`}>
      {item.aspect}
      <span className="ml-1 opacity-60">·{item.count}</span>
    </span>
  )
}

// ─── Main Dashboard Page ───────────────────────────────────────────────────────
export default function Dashboard() {
  const { filters, setFilters, isChatOpen, setChatOpen, resetLiveReviews } = useDashboardStore()
  const period = filters.period

  // Reset live new-review counter when user navigates to dashboard
  useEffect(() => {
    resetLiveReviews()
  }, [resetLiveReviews])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard', period],
    queryFn: () => dashboardApi.getDashboard(period),
    refetchInterval: 30_000,
    staleTime: 15_000,
  })

  const { data: insights = [] } = useQuery({
    queryKey: ['insights', period],
    queryFn: () => insightsApi.getInsights(period),
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const kpis = useMemo(() => data?.kpis, [data])
  const trend = useMemo(() => data?.trend?.points ?? [], [data])
  const langs = useMemo(() => data?.language_distribution ?? [], [data])
  const sources = useMemo(() => data?.source_breakdown ?? [], [data])
  const aspects = useMemo(() => data?.aspect_sentiments ?? [], [data])
  const keywords = useMemo(() => data?.top_keywords ?? [], [data])
  const delta = kpis?.change_from_last_period?.sentiment_score

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Dashboard" subtitle="Real-time sentiment overview" />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Period filter row */}
        <div className="flex items-center justify-between">
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
            {isLoading ? 'Loading…' : isError ? 'Failed to load data' : `Showing last ${period}`}
          </p>
          <PeriodFilter value={period} onChange={(p) => setFilters({ period: p as typeof period })} />
        </div>

        {/* ── KPI Cards ──────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {/* Sentiment face card */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-5 flex flex-col items-center justify-center gap-2 col-span-2 lg:col-span-1"
          >
            <SentimentFace score={kpis?.overall_sentiment_score ?? 0} />
            <p className="text-xs font-medium text-white/50">Overall Mood</p>
            <p className="text-lg font-bold text-white">
              {kpis ? (kpis.overall_sentiment_score >= 0.05 ? 'Positive' : kpis.overall_sentiment_score <= -0.05 ? 'Negative' : 'Neutral') : '—'}
            </p>
          </motion.div>

          <KPICard
            label="Total Reviews"
            value={kpis?.total_reviews ?? 0}
            icon={MessageSquare}
            color="#7c3aed"
            delta={undefined}
          />
          <KPICard
            label="Positive"
            value={kpis?.positive_percent ?? 0}
            suffix="%"
            icon={TrendingUp}
            color="#10b981"
          />
          <KPICard
            label="Negative"
            value={kpis?.negative_percent ?? 0}
            suffix="%"
            icon={TrendingDown}
            color="#f87171"
          />
          <KPICard
            label="Neutral"
            value={kpis?.neutral_percent ?? 0}
            suffix="%"
            icon={Minus}
            color="#94a3b8"
          />
          <KPICard
            label="Languages"
            value={kpis?.active_languages ?? 0}
            icon={Globe}
            color="#06b6d4"
            delta={delta}
          />
        </div>

        {/* ── Trend + Language ───────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Trend chart — 2/3 width */}
          <div className="glass-card p-5 lg:col-span-2">
            <p className="text-sm font-semibold text-white mb-4">Sentiment Trend</p>
            <TrendChart points={trend} />
          </div>

          {/* Language donut — 1/3 width */}
          <div className="glass-card p-5">
            <p className="text-sm font-semibold text-white mb-4">Language Distribution</p>
            <LanguageDonut data={langs} />
          </div>
        </div>

        {/* ── Source + AI Insights ───────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Source bar — 1/3 */}
          <div className="glass-card p-5">
            <p className="text-sm font-semibold text-white mb-4">Source Breakdown</p>
            <SourceBar data={sources} />
          </div>

          {/* AI Insights — 2/3 */}
          <div className="glass-card p-5 lg:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div
                className="w-6 h-6 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(124,58,237,0.2)' }}
              >
                <Zap size={13} className="text-brand-400" />
              </div>
              <p className="text-sm font-semibold text-white">AI Insights</p>
            </div>

            {insights.length === 0 ? (
              <div className="py-6 text-center">
                <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  Upload reviews to generate AI insights
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {insights.map((item, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}>
                    <InsightCard item={item} />
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Aspects + Keywords ─────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Aspect badges */}
          <div className="glass-card p-5">
            <p className="text-sm font-semibold text-white mb-4">Aspect Sentiment</p>
            {aspects.length === 0 ? (
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>No aspect data yet</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {aspects.slice(0, 18).map((a, i) => (
                  <motion.div
                    key={a.aspect}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.04 }}
                  >
                    <AspectBadge item={a} />
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Keyword pills */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Hash size={14} style={{ color: 'rgba(255,255,255,0.4)' }} />
              <p className="text-sm font-semibold text-white">Top Keywords</p>
            </div>
            {keywords.length === 0 ? (
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>No keywords extracted yet</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {keywords.map((kw: any, i: number) => (
                  <motion.span
                    key={kw.keyword}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className="px-3 py-1.5 rounded-full text-xs font-medium"
                    style={{
                      background: 'rgba(124,58,237,0.12)',
                      border: '1px solid rgba(124,58,237,0.25)',
                      color: 'rgba(167,139,250,0.9)',
                    }}
                  >
                    {kw.keyword}
                    <span className="ml-1.5 opacity-50 text-xs">{kw.count}</span>
                  </motion.span>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Chat slide-in panel */}
      <ChatPanel isOpen={isChatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
