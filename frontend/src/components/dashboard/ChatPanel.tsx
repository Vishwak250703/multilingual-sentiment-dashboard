import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Send, X, ChevronRight, RotateCcw } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
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

// ─── Constants ────────────────────────────────────────────────────────────────
const SUGGESTIONS = [
  'What are customers complaining about most?',
  'Which aspects have the worst sentiment?',
  'Which source has the most negative reviews?',
  'What are the top positive keywords?',
]

const CHART_COLORS = ['#7c3aed', '#2563eb', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']

// ─── Inline chart renderer ────────────────────────────────────────────────────
function InlineChart({ chart }: { chart: ChartData }) {
  if (!chart.data?.length) return null

  const commonAxis = {
    tick: { fill: 'rgba(255,255,255,0.45)', fontSize: 10 },
    axisLine: false,
    tickLine: false,
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
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={chart.data as any[]}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={70}
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
        <ResponsiveContainer width="100%" height={160}>
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
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={chart.data as any[]} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
            <defs>
              <linearGradient id="chatBarGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.9} />
                <stop offset="100%" stopColor="#2563eb" stopOpacity={0.9} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey={chart.x_key ?? 'label'} {...commonAxis} />
            <YAxis {...commonAxis} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={chart.y_key ?? 'value'} fill="url(#chatBarGrad)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

// ─── Typing indicator ─────────────────────────────────────────────────────────
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

// ─── Message bubbles ──────────────────────────────────────────────────────────
function UserBubble({ content }: { content: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-end"
    >
      <div
        className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed text-white"
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
      className="flex items-start gap-2"
    >
      <div
        className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ background: 'rgba(124,58,237,0.25)', border: '1px solid rgba(124,58,237,0.3)' }}
      >
        <MessageSquare size={11} style={{ color: '#a78bfa' }} />
      </div>

      <div className="flex-1 max-w-[90%]">
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
          <div className="mt-2 space-y-1.5">
            <p className="text-xs text-white/30 px-1">Supporting reviews:</p>
            {message.supporting_reviews.map((r) => (
              <div
                key={r.id}
                className="px-3 py-2 rounded-xl text-xs"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: sentimentColor(r.sentiment) }}
                  />
                  <span className="text-white/40 capitalize">{r.source}</span>
                </div>
                <p className="text-white/60 leading-relaxed">{r.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Main ChatPanel ────────────────────────────────────────────────────────────
export function ChatPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Build conversation history from messages for the API
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

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, mutation.isPending])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) setTimeout(() => textareaRef.current?.focus(), 300)
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 28, stiffness: 280 }}
          className="fixed top-0 right-0 h-full w-96 z-50 flex flex-col"
          style={{
            background: 'rgba(10,10,20,0.96)',
            borderLeft: '1px solid rgba(124,58,237,0.2)',
            backdropFilter: 'blur(24px)',
          }}
        >
          {/* ── Header ────────────────────────────────────────────── */}
          <div
            className="flex items-center justify-between px-5 py-4 flex-shrink-0"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}
          >
            <div className="flex items-center gap-2.5">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(124,58,237,0.2)', border: '1px solid rgba(124,58,237,0.3)' }}
              >
                <MessageSquare size={15} style={{ color: '#a78bfa' }} />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">Chat with Data</p>
                <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  Ask anything about your reviews
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button
                  onClick={() => setMessages([])}
                  className="p-1.5 rounded-lg transition-colors"
                  style={{ color: 'rgba(255,255,255,0.35)' }}
                  title="Clear conversation"
                >
                  <RotateCcw size={13} />
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg transition-colors hover:text-white"
                style={{ color: 'rgba(255,255,255,0.35)' }}
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* ── Messages ─────────────────────────────────────────── */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {messages.length === 0 ? (
              /* Empty state — suggestions */
              <div className="h-full flex flex-col items-center justify-center gap-5 py-8">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center"
                  style={{ background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.2)' }}
                >
                  <MessageSquare size={24} style={{ color: 'rgba(167,139,250,0.6)' }} />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-white mb-1">Ask about your data</p>
                  <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.4)' }}>
                    I'll search your review database and answer with real data
                  </p>
                </div>
                <div className="w-full space-y-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="w-full flex items-center gap-2 p-3 rounded-xl text-left text-xs transition-all duration-200"
                      style={{
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.07)',
                        color: 'rgba(255,255,255,0.6)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(124,58,237,0.1)'
                        e.currentTarget.style.borderColor = 'rgba(124,58,237,0.25)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
                        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'
                      }}
                    >
                      <ChevronRight size={12} style={{ color: '#a78bfa', flexShrink: 0 }} />
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
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
                className="flex items-start gap-2"
              >
                <div
                  className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(124,58,237,0.25)', border: '1px solid rgba(124,58,237,0.3)' }}
                >
                  <MessageSquare size={11} style={{ color: '#a78bfa' }} />
                </div>
                <div
                  className="rounded-2xl rounded-tl-sm"
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  <TypingIndicator />
                </div>
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* ── Input area ───────────────────────────────────────── */}
          <div
            className="px-4 py-4 flex-shrink-0"
            style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}
          >
            <div
              className="flex items-end gap-2 rounded-2xl p-2"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your reviews…"
                rows={1}
                className="flex-1 resize-none bg-transparent text-sm text-white outline-none px-2 py-1.5"
                style={{
                  color: 'rgba(255,255,255,0.9)',
                  maxHeight: '96px',
                  scrollbarWidth: 'none',
                }}
                onInput={(e) => {
                  const t = e.currentTarget
                  t.style.height = 'auto'
                  t.style.height = Math.min(t.scrollHeight, 96) + 'px'
                }}
              />
              <button
                onClick={() => send(input)}
                disabled={!input.trim() || mutation.isPending}
                className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 disabled:opacity-30"
                style={{ background: 'linear-gradient(135deg, #7c3aed, #2563eb)' }}
              >
                <Send size={13} className="text-white" />
              </button>
            </div>
            <p className="text-center text-xs mt-2" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Enter to send · Shift+Enter for new line
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
