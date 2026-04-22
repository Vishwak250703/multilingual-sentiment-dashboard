import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquare, Send, RotateCcw, ChevronRight,
  Sparkles, TrendingUp, AlertTriangle, Activity,
} from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

import { TopBar } from '@/components/layout/TopBar'
import { chatApi } from '@/api/endpoints'
import type { ChatMessage, ChartData } from '@/types'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Message {
  role: 'user' | 'assistant'
  content: string
  chart?: ChartData
  supporting_reviews?: Array<{ id: string; text: string; sentiment: string; source: string }>
  isError?: boolean
}

// ─── Question categories ──────────────────────────────────────────────────────
const QUESTION_CATEGORIES = [
  {
    label: 'Volume & Trends',
    icon: TrendingUp,
    color: '#7c3aed',
    questions: [
      'How has sentiment changed over the past week?',
      'Which day had the highest review volume?',
      'What is the overall sentiment score?',
    ],
  },
  {
    label: 'Issues & Complaints',
    icon: AlertTriangle,
    color: '#f59e0b',
    questions: [
      'What are customers complaining about most?',
      'Which aspects have the worst sentiment?',
      'Show me the most critical negative reviews',
    ],
  },
  {
    label: 'Positive Feedback',
    icon: Sparkles,
    color: '#10b981',
    questions: [
      'What do customers love most?',
      'What are the top positive keywords?',
      'Which source has the best sentiment?',
    ],
  },
  {
    label: 'Comparison',
    icon: Activity,
    color: '#06b6d4',
    questions: [
      'Which language group has the most negative feedback?',
      'Compare sentiment across different sources',
      'Which product or branch performs best?',
    ],
  },
]

const CHART_COLORS = ['#7c3aed', '#2563eb', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']

// ─── Inline Chart ─────────────────────────────────────────────────────────────
function InlineChart({ chart }: { chart: ChartData }) {
  if (!chart.data?.length) return null

  const commonAxis = {
    tick: { fill: 'rgba(255,255,255,0.45)', fontSize: 10 },
    axisLine: false as const,
    tickLine: false as const,
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div
        className="rounded-xl px-3 py-2 text-xs"
        style={{
          background: 'rgba(15,15,25,0.95)',
          border: '1px solid rgba(124,58,237,0.3)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <p className="text-white/60 mb-1">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} style={{ color: p.color ?? '#a78bfa' }}>
            {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
          </p>
        ))}
      </div>
    )
  }

  return (
    <div
      className="mt-3 rounded-xl p-3"
      style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <p className="text-xs font-semibold text-white/70 mb-3">{chart.title}</p>

      {chart.chart_type === 'pie' ? (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chart.data as any[]}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={80}
              paddingAngle={2}
            >
              {(chart.data as any[]).map((_: any, i: number) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      ) : chart.chart_type === 'line' ? (
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={chart.data as any[]} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={chart.x_key ?? 'label'} {...commonAxis} />
            <YAxis {...commonAxis} />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey={chart.y_key ?? 'value'}
              stroke="#7c3aed"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chart.data as any[]} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
            <defs>
              <linearGradient id="chatPageBarGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.9} />
                <stop offset="100%" stopColor="#2563eb" stopOpacity={0.9} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={chart.x_key ?? 'label'} {...commonAxis} />
            <YAxis {...commonAxis} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={chart.y_key ?? 'value'} fill="url(#chatPageBarGrad)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

// ─── Typing Indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: 'rgba(167,139,250,0.7)' }}
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  )
}

// ─── Message Bubbles ──────────────────────────────────────────────────────────
function UserBubble({ content }: { content: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-end"
    >
      <div
        className="max-w-[78%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm leading-relaxed text-white"
        style={{ background: 'linear-gradient(135deg, #7c3aed, #2563eb)' }}
      >
        {content}
      </div>
    </motion.div>
  )
}

function AssistantBubble({ message }: { message: Message }) {
  const sentimentColor = (s: string) =>
    s === 'positive' ? '#4ade80' : s === 'negative' ? '#f87171' : '#94a3b8'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3"
    >
      <div
        className="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ background: 'rgba(124,58,237,0.25)', border: '1px solid rgba(124,58,237,0.3)' }}
      >
        <MessageSquare size={12} style={{ color: '#a78bfa' }} />
      </div>

      <div className="flex-1 max-w-[88%]">
        {/* Answer text */}
        <div
          className="px-4 py-3 rounded-2xl rounded-tl-sm text-sm leading-relaxed"
          style={{
            background: message.isError ? 'rgba(239,68,68,0.08)' : 'rgba(255,255,255,0.05)',
            border: message.isError
              ? '1px solid rgba(239,68,68,0.2)'
              : '1px solid rgba(255,255,255,0.08)',
            color: message.isError ? '#fca5a5' : 'rgba(255,255,255,0.85)',
            whiteSpace: 'pre-wrap',
          }}
        >
          {message.content}
        </div>

        {/* Inline chart */}
        {message.chart && <InlineChart chart={message.chart} />}

        {/* Supporting reviews */}
        {message.supporting_reviews && message.supporting_reviews.length > 0 && (
          <div className="mt-2.5 space-y-2">
            <p className="text-xs px-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
              Supporting reviews:
            </p>
            {message.supporting_reviews.map((r) => (
              <div
                key={r.id}
                className="px-3 py-2.5 rounded-xl text-xs"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: sentimentColor(r.sentiment) }}
                  />
                  <span className="capitalize" style={{ color: 'rgba(255,255,255,0.4)' }}>
                    {r.source}
                  </span>
                </div>
                <p className="leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  {r.text}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Build conversation history for the API
  const history: ChatMessage[] = messages.map((m) => ({
    role: m.role,
    content: m.content,
  }))

  const mutation = useMutation({
    mutationFn: (question: string) => chatApi.ask(question, history),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          chart: data.chart ?? undefined,
          supporting_reviews: (data.supporting_reviews ?? []) as Message['supporting_reviews'],
        },
      ])
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Something went wrong. Please try again.',
          isError: true,
        },
      ])
    },
  })

  const send = (text: string) => {
    const q = text.trim()
    if (!q || mutation.isPending) return
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setInput('')
    mutation.mutate(q)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, mutation.isPending])

  // Focus textarea on page mount
  useEffect(() => {
    const timer = setTimeout(() => textareaRef.current?.focus(), 200)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Chat with Data" subtitle="Ask questions about your review data" />

      {/* Two-column layout: suggestions | chat */}
      <div className="flex-1 flex overflow-hidden p-6 gap-5">

        {/* ── Left: Suggested Questions ───────────────────────────── */}
        <div
          className="w-72 flex-shrink-0 flex flex-col glass-card p-4 overflow-y-auto"
          style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.1) transparent' }}
        >
          <div className="flex items-center justify-between mb-4">
            <p
              className="text-[11px] font-semibold uppercase tracking-wider"
              style={{ color: 'rgba(255,255,255,0.4)' }}
            >
              Suggested Questions
            </p>
            <AnimatePresence>
              {messages.length > 0 && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  onClick={() => setMessages([])}
                  className="flex items-center gap-1 text-xs transition-colors"
                  style={{ color: 'rgba(255,255,255,0.3)' }}
                  title="Clear conversation"
                >
                  <RotateCcw size={11} />
                  Clear
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          <div className="space-y-5">
            {QUESTION_CATEGORIES.map((cat) => {
              const CatIcon = cat.icon
              return (
                <div key={cat.label}>
                  {/* Category header */}
                  <div className="flex items-center gap-1.5 mb-2">
                    <CatIcon size={11} style={{ color: cat.color }} />
                    <p
                      className="text-[11px] font-semibold uppercase tracking-wider"
                      style={{ color: cat.color }}
                    >
                      {cat.label}
                    </p>
                  </div>

                  {/* Question buttons */}
                  <div className="space-y-1">
                    {cat.questions.map((q) => (
                      <button
                        key={q}
                        onClick={() => send(q)}
                        disabled={mutation.isPending}
                        className="w-full flex items-start gap-2 p-2.5 rounded-xl text-left text-xs transition-all duration-200 disabled:opacity-40"
                        style={{
                          background: 'rgba(255,255,255,0.03)',
                          border: '1px solid rgba(255,255,255,0.06)',
                          color: 'rgba(255,255,255,0.55)',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = `${cat.color}18`
                          e.currentTarget.style.borderColor = `${cat.color}38`
                          e.currentTarget.style.color = 'rgba(255,255,255,0.85)'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'
                          e.currentTarget.style.color = 'rgba(255,255,255,0.55)'
                        }}
                      >
                        <ChevronRight
                          size={10}
                          style={{ color: cat.color, flexShrink: 0, marginTop: '2px' }}
                        />
                        <span className="leading-relaxed">{q}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Right: Chat area ──────────────────────────────────────── */}
        <div className="flex-1 flex flex-col glass-card overflow-hidden">

          {/* Messages list */}
          <div
            className="flex-1 overflow-y-auto px-6 py-5 space-y-5"
            style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.08) transparent' }}
          >
            {messages.length === 0 ? (
              /* Empty state */
              <div className="h-full flex flex-col items-center justify-center gap-6 py-12">
                <div
                  className="w-16 h-16 rounded-3xl flex items-center justify-center"
                  style={{
                    background: 'rgba(124,58,237,0.12)',
                    border: '1px solid rgba(124,58,237,0.2)',
                  }}
                >
                  <MessageSquare size={28} style={{ color: 'rgba(167,139,250,0.6)' }} />
                </div>
                <div className="text-center max-w-md">
                  <p className="text-base font-semibold text-white mb-2">
                    Ask anything about your data
                  </p>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: 'rgba(255,255,255,0.4)' }}
                  >
                    I'll search your review database using semantic search and answer with real
                    data, charts, and supporting reviews.
                  </p>
                </div>
                {/* Quick-start chips */}
                <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                  {[
                    'What are customers complaining about?',
                    'Show sentiment trend',
                    'Top keywords this week',
                  ].map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="px-3 py-1.5 rounded-xl text-xs transition-all duration-200"
                      style={{
                        background: 'rgba(124,58,237,0.1)',
                        border: '1px solid rgba(124,58,237,0.2)',
                        color: '#a78bfa',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(124,58,237,0.2)'
                        e.currentTarget.style.borderColor = 'rgba(124,58,237,0.4)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(124,58,237,0.1)'
                        e.currentTarget.style.borderColor = 'rgba(124,58,237,0.2)'
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Message history */
              messages.map((msg, i) =>
                msg.role === 'user' ? (
                  <UserBubble key={i} content={msg.content} />
                ) : (
                  <AssistantBubble key={i} message={msg} />
                )
              )
            )}

            {/* Typing indicator */}
            {mutation.isPending && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-start gap-3"
              >
                <div
                  className="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{
                    background: 'rgba(124,58,237,0.25)',
                    border: '1px solid rgba(124,58,237,0.3)',
                  }}
                >
                  <MessageSquare size={12} style={{ color: '#a78bfa' }} />
                </div>
                <div
                  className="rounded-2xl rounded-tl-sm"
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.08)',
                  }}
                >
                  <TypingIndicator />
                </div>
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div
            className="px-6 py-4 flex-shrink-0"
            style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}
          >
            <div
              className="flex items-end gap-3 rounded-2xl p-2.5"
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
              }}
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your reviews… (Enter to send)"
                rows={1}
                className="flex-1 resize-none bg-transparent text-sm outline-none px-2 py-1.5"
                style={{
                  color: 'rgba(255,255,255,0.9)',
                  maxHeight: '120px',
                  scrollbarWidth: 'none',
                }}
                onInput={(e) => {
                  const t = e.currentTarget
                  t.style.height = 'auto'
                  t.style.height = Math.min(t.scrollHeight, 120) + 'px'
                }}
              />
              <button
                onClick={() => send(input)}
                disabled={!input.trim() || mutation.isPending}
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 disabled:opacity-30"
                style={{ background: 'linear-gradient(135deg, #7c3aed, #2563eb)' }}
              >
                <Send size={14} className="text-white" />
              </button>
            </div>
            <p
              className="text-center text-xs mt-2"
              style={{ color: 'rgba(255,255,255,0.2)' }}
            >
              Shift+Enter for new line · Powered by Claude AI + semantic search
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
