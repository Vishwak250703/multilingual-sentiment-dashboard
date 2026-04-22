import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Filter, X, ChevronLeft, ChevronRight, FileText,
  Globe, Tag, Zap, Check, AlertCircle, Edit3, Download,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { TopBar } from '@/components/layout/TopBar'
import { reviewsApi } from '@/api/endpoints'
import { useAuthStore } from '@/store/authStore'
import type { Review, Sentiment } from '@/types'

// ─── Filter state ─────────────────────────────────────────────────────────────
interface Filters {
  sentiment: string
  source: string
  language: string
  date_from: string
  date_to: string
  page: number
  page_size: number
}

const DEFAULT_FILTERS: Filters = {
  sentiment: '',
  source: '',
  language: '',
  date_from: '',
  date_to: '',
  page: 1,
  page_size: 20,
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function sentimentClass(s?: string | null) {
  if (s === 'positive') return 'badge-positive'
  if (s === 'negative') return 'badge-negative'
  return 'badge-neutral'
}

function sentimentLabel(s?: string | null) {
  if (!s) return 'Unknown'
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function scoreColor(score?: number | null) {
  if (score == null) return 'rgba(255,255,255,0.3)'
  if (score >= 0.1) return '#4ade80'
  if (score <= -0.1) return '#f87171'
  return '#94a3b8'
}

function statusStyle(status: string) {
  switch (status) {
    case 'completed': return { bg: 'rgba(74,222,128,0.1)', color: '#4ade80', border: 'rgba(74,222,128,0.2)' }
    case 'processing': return { bg: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: 'rgba(251,191,36,0.2)' }
    case 'failed': return { bg: 'rgba(248,113,113,0.1)', color: '#f87171', border: 'rgba(248,113,113,0.2)' }
    default: return { bg: 'rgba(148,163,184,0.1)', color: '#94a3b8', border: 'rgba(148,163,184,0.2)' }
  }
}

function formatDate(d?: string | null) {
  if (!d) return '—'
  try { return format(new Date(d), 'MMM d, yyyy') } catch { return '—' }
}

// ─── Select styled input ─────────────────────────────────────────────────────
const selectStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '0.75rem',
  color: 'rgba(255,255,255,0.85)',
  padding: '0.5rem 0.875rem',
  fontSize: '0.8125rem',
  outline: 'none',
  appearance: 'none',
  WebkitAppearance: 'none',
  cursor: 'pointer',
}

// ─── Review Drawer ────────────────────────────────────────────────────────────
function ReviewDrawer({
  reviewId,
  onClose,
  userRole,
}: {
  reviewId: string
  onClose: () => void
  userRole: string
}) {
  const queryClient = useQueryClient()
  const [showCorrect, setShowCorrect] = useState(false)
  const [newSentiment, setNewSentiment] = useState<Sentiment>('positive')
  const [note, setNote] = useState('')

  const { data: review, isLoading } = useQuery({
    queryKey: ['review', reviewId],
    queryFn: () => reviewsApi.get(reviewId),
    enabled: !!reviewId,
  })

  const correction = useMutation({
    mutationFn: () =>
      reviewsApi.correct(reviewId, { corrected_sentiment: newSentiment, note: note || undefined }),
    onSuccess: () => {
      toast.success('Sentiment corrected successfully')
      queryClient.invalidateQueries({ queryKey: ['review', reviewId] })
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
      setShowCorrect(false)
      setNote('')
    },
    onError: () => toast.error('Failed to save correction'),
  })

  const canCorrect = userRole === 'admin' || userRole === 'analyst'

  const displayText = review?.translated_text || review?.raw_text || ''
  const sentences: Array<{ sentence: string; sentiment: string; score: number }> =
    Array.isArray(review?.sentence_sentiments) ? (review.sentence_sentiments as any[]) : []
  const aspects: Record<string, string> = review?.aspects ?? {}
  const keywords: string[] = Array.isArray(review?.keywords) ? (review.keywords as string[]) : []

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 28, stiffness: 280 }}
      className="fixed top-0 right-0 h-full w-[520px] z-[55] flex flex-col overflow-hidden"
      style={{
        background: 'rgba(10,10,20,0.97)',
        borderLeft: '1px solid rgba(124,58,237,0.2)',
        backdropFilter: 'blur(24px)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: 'rgba(124,58,237,0.2)', border: '1px solid rgba(124,58,237,0.3)' }}
          >
            <FileText size={15} style={{ color: '#a78bfa' }} />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Review Detail</p>
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
              {review ? `${review.source} · ${formatDate(review.review_date ?? review.created_at)}` : 'Loading…'}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg transition-colors hover:bg-white/10"
          style={{ color: 'rgba(255,255,255,0.4)' }}
        >
          <X size={15} />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        ) : review ? (
          <>
            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-2">
              <span className={sentimentClass(review.sentiment)}>
                {sentimentLabel(review.sentiment)}
              </span>
              {review.sentiment_score != null && (
                <span
                  className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
                  style={{ color: scoreColor(review.sentiment_score), background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                >
                  {review.sentiment_score >= 0 ? '+' : ''}{review.sentiment_score.toFixed(3)}
                </span>
              )}
              {review.confidence != null && (
                <span className="px-2.5 py-0.5 rounded-full text-xs" style={{ color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  {Math.round(review.confidence * 100)}% confidence
                </span>
              )}
              <span className="px-2.5 py-0.5 rounded-full text-xs capitalize" style={{ color: 'rgba(255,255,255,0.5)', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                {review.source}
              </span>
              {review.detected_language && (
                <span className="px-2.5 py-0.5 rounded-full text-xs uppercase" style={{ color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  {review.detected_language}
                </span>
              )}
            </div>

            {/* Review text */}
            <div>
              <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {review.translated_text ? 'Translated Text' : 'Review Text'}
              </p>
              <div
                className="p-4 rounded-xl text-sm leading-relaxed"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.85)' }}
              >
                {displayText}
              </div>
              {review.translated_text && review.raw_text !== review.translated_text && (
                <details className="mt-2">
                  <summary className="text-xs cursor-pointer" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    Show original ({review.detected_language})
                  </summary>
                  <div className="mt-1 p-3 rounded-xl text-xs leading-relaxed" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.55)' }}>
                    {review.raw_text}
                  </div>
                </details>
              )}
            </div>

            {/* Sentence sentiments */}
            {sentences.length > 0 && (
              <div>
                <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Sentence Breakdown
                </p>
                <div className="space-y-2">
                  {sentences.map((s, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 p-3 rounded-xl text-xs"
                      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                    >
                      <span className={`${sentimentClass(s.sentiment)} flex-shrink-0 mt-0.5`}>
                        {s.sentiment}
                      </span>
                      <span className="leading-relaxed flex-1" style={{ color: 'rgba(255,255,255,0.7)' }}>
                        {s.sentence}
                      </span>
                      <span className="flex-shrink-0 font-mono text-xs" style={{ color: scoreColor(s.score) }}>
                        {s.score >= 0 ? '+' : ''}{s.score.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Aspects */}
            {Object.keys(aspects).length > 0 && (
              <div>
                <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Aspect Sentiment
                </p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(aspects).map(([aspect, sentiment]) => (
                    <span key={aspect} className={`${sentimentClass(sentiment)} capitalize`}>
                      {aspect}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Keywords */}
            {keywords.length > 0 && (
              <div>
                <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Keywords
                </p>
                <div className="flex flex-wrap gap-2">
                  {keywords.map((kw) => (
                    <span
                      key={kw}
                      className="px-2.5 py-0.5 rounded-full text-xs"
                      style={{ background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.2)', color: 'rgba(167,139,250,0.9)' }}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Correction panel */}
            {canCorrect && (
              <div>
                <AnimatePresence>
                  {!showCorrect ? (
                    <motion.button
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      onClick={() => {
                        setNewSentiment((review.sentiment as Sentiment) ?? 'neutral')
                        setShowCorrect(true)
                      }}
                      className="btn-ghost text-xs w-full justify-center"
                    >
                      <Edit3 size={13} />
                      Correct Sentiment
                    </motion.button>
                  ) : (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="p-4 rounded-xl space-y-3"
                      style={{ background: 'rgba(124,58,237,0.06)', border: '1px solid rgba(124,58,237,0.2)' }}
                    >
                      <p className="text-xs font-semibold text-white">Correct Sentiment Label</p>

                      {/* Sentiment picker */}
                      <div className="flex gap-2">
                        {(['positive', 'negative', 'neutral'] as Sentiment[]).map((s) => (
                          <button
                            key={s}
                            onClick={() => setNewSentiment(s)}
                            className={`flex-1 py-2 rounded-xl text-xs font-semibold capitalize transition-all duration-150 ${sentimentClass(s)}`}
                            style={{
                              opacity: newSentiment === s ? 1 : 0.4,
                              transform: newSentiment === s ? 'scale(1.03)' : 'scale(1)',
                            }}
                          >
                            {s}
                          </button>
                        ))}
                      </div>

                      {/* Note */}
                      <textarea
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Optional note (reason for correction…)"
                        rows={2}
                        className="input-glass text-xs resize-none"
                        style={{ padding: '0.5rem 0.75rem' }}
                      />

                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => correction.mutate()}
                          disabled={correction.isPending}
                          className="btn-primary text-xs flex-1 justify-center"
                        >
                          {correction.isPending ? (
                            <span className="w-3.5 h-3.5 rounded-full border border-white/60 border-t-transparent animate-spin" />
                          ) : (
                            <Check size={13} />
                          )}
                          Save Correction
                        </button>
                        <button
                          onClick={() => { setShowCorrect(false); setNote('') }}
                          className="btn-ghost text-xs px-3"
                        >
                          Cancel
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <AlertCircle size={24} style={{ color: 'rgba(255,255,255,0.2)' }} />
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Review not found</p>
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Main Reviews Page ────────────────────────────────────────────────────────
export default function Reviews() {
  const { user } = useAuthStore()
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)

  const updateFilter = (patch: Partial<Filters>) =>
    setFilters((prev) => ({ ...prev, ...patch, page: 'page' in patch ? (patch.page ?? 1) : 1 }))

  // Build API params — only pass non-empty values
  const apiParams: Record<string, string | number> = {
    page: filters.page,
    page_size: filters.page_size,
  }
  if (filters.sentiment) apiParams.sentiment = filters.sentiment
  if (filters.source)    apiParams.source    = filters.source
  if (filters.language)  apiParams.language  = filters.language
  if (filters.date_from) apiParams.date_from = filters.date_from
  if (filters.date_to)   apiParams.date_to   = filters.date_to

  const handleExport = async () => {
    setExporting(true)
    try {
      await reviewsApi.exportCsv(apiParams)
      toast.success('CSV downloaded')
    } catch {
      toast.error('Export failed')
    } finally {
      setExporting(false)
    }
  }

  const handleExportPdf = async () => {
    setExportingPdf(true)
    try {
      await reviewsApi.exportPdf(apiParams)
      toast.success('PDF downloaded')
    } catch {
      toast.error('PDF export failed')
    } finally {
      setExportingPdf(false)
    }
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['reviews', apiParams],
    queryFn: () => reviewsApi.list(apiParams),
    placeholderData: (prev) => prev,
  })

  const reviews = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  const hasActiveFilters = !!(filters.sentiment || filters.source || filters.language || filters.date_from || filters.date_to)

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Reviews" subtitle="Drill-down review analysis" />

      <div className="flex-1 overflow-y-auto p-6 space-y-4">

        {/* ── Filter Bar ────────────────────────────────────────── */}
        <div className="glass-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>
              <Filter size={13} />
              Filters
            </div>

            {/* Sentiment */}
            <select
              value={filters.sentiment}
              onChange={(e) => updateFilter({ sentiment: e.target.value })}
              style={selectStyle}
            >
              <option value="">All Sentiments</option>
              <option value="positive">Positive</option>
              <option value="negative">Negative</option>
              <option value="neutral">Neutral</option>
            </select>

            {/* Source */}
            <select
              value={filters.source}
              onChange={(e) => updateFilter({ source: e.target.value })}
              style={selectStyle}
            >
              <option value="">All Sources</option>
              <option value="csv">CSV</option>
              <option value="api">API</option>
              <option value="webhook">Webhook</option>
              <option value="app_review">App Review</option>
              <option value="social">Social</option>
              <option value="chat_log">Chat Log</option>
              <option value="support_ticket">Support Ticket</option>
            </select>

            {/* Language */}
            <input
              type="text"
              value={filters.language}
              onChange={(e) => updateFilter({ language: e.target.value.toLowerCase() })}
              placeholder="Language code (e.g. en)"
              className="input-glass text-xs"
              style={{ width: '160px', padding: '0.5rem 0.875rem' }}
            />

            {/* Date From */}
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => updateFilter({ date_from: e.target.value })}
              className="input-glass text-xs"
              style={{ width: '150px', padding: '0.5rem 0.875rem', colorScheme: 'dark' }}
            />

            {/* Date To */}
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => updateFilter({ date_to: e.target.value })}
              className="input-glass text-xs"
              style={{ width: '150px', padding: '0.5rem 0.875rem', colorScheme: 'dark' }}
            />

            {/* Clear */}
            {hasActiveFilters && (
              <button
                onClick={() => setFilters(DEFAULT_FILTERS)}
                className="btn-ghost text-xs px-3 py-2"
              >
                <X size={12} />
                Clear
              </button>
            )}

            {/* Total count + Export */}
            <div className="ml-auto flex items-center gap-3">
              <span className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                {isLoading ? 'Loading…' : `${total.toLocaleString()} review${total !== 1 ? 's' : ''}`}
              </span>
              <button
                onClick={handleExport}
                disabled={exporting || total === 0}
                className="btn-ghost text-xs px-3 py-2 disabled:opacity-40"
              >
                {exporting
                  ? <span className="w-3 h-3 rounded-full border border-white/60 border-t-transparent animate-spin" />
                  : <Download size={13} />
                }
                Export CSV
              </button>
              <button
                onClick={handleExportPdf}
                disabled={exportingPdf || total === 0}
                className="btn-ghost text-xs px-3 py-2 disabled:opacity-40"
              >
                {exportingPdf
                  ? <span className="w-3 h-3 rounded-full border border-white/60 border-t-transparent animate-spin" />
                  : <FileText size={13} />
                }
                Export PDF
              </button>
            </div>
          </div>
        </div>

        {/* ── Table ─────────────────────────────────────────────── */}
        <div className="glass-card overflow-hidden">
          {isError ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <AlertCircle size={24} style={{ color: '#f87171' }} />
              <p className="text-sm text-red-400">Failed to load reviews</p>
            </div>
          ) : isLoading && reviews.length === 0 ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-6 h-6 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          ) : reviews.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.05)' }}>
                <FileText size={20} style={{ color: 'rgba(255,255,255,0.2)' }} />
              </div>
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {hasActiveFilters ? 'No reviews match your filters' : 'No reviews yet — upload a CSV to get started'}
              </p>
            </div>
          ) : (
            <>
              {/* Table header */}
              <div
                className="grid text-xs font-semibold px-5 py-3"
                style={{
                  gridTemplateColumns: '140px 1fr 80px 90px 110px 80px 90px',
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                  color: 'rgba(255,255,255,0.35)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                <span>Date</span>
                <span>Review Text</span>
                <span>Lang</span>
                <span>Source</span>
                <span>Sentiment</span>
                <span>Score</span>
                <span>Status</span>
              </div>

              {/* Table rows */}
              <div>
                {reviews.map((review, i) => {
                  const ss = statusStyle(review.processing_status)
                  return (
                    <motion.div
                      key={review.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.02 }}
                      onClick={() => setSelectedId(selectedId === review.id ? null : review.id)}
                      className="grid items-center px-5 py-3.5 cursor-pointer transition-all duration-150"
                      style={{
                        gridTemplateColumns: '140px 1fr 80px 90px 110px 80px 90px',
                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                        background: selectedId === review.id
                          ? 'rgba(124,58,237,0.08)'
                          : 'transparent',
                      }}
                      onMouseEnter={(e) => {
                        if (selectedId !== review.id)
                          e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                      }}
                      onMouseLeave={(e) => {
                        if (selectedId !== review.id)
                          e.currentTarget.style.background = 'transparent'
                      }}
                    >
                      {/* Date */}
                      <span className="text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>
                        {formatDate(review.review_date ?? review.created_at)}
                      </span>

                      {/* Text snippet */}
                      <span
                        className="text-xs pr-4 truncate"
                        style={{ color: 'rgba(255,255,255,0.75)' }}
                        title={review.translated_text ?? review.raw_text}
                      >
                        {(review.translated_text ?? review.raw_text).slice(0, 120)}
                      </span>

                      {/* Language */}
                      <span className="text-xs uppercase font-mono" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        {review.detected_language ?? review.original_language ?? '—'}
                      </span>

                      {/* Source */}
                      <span className="text-xs capitalize" style={{ color: 'rgba(255,255,255,0.45)' }}>
                        {review.source}
                      </span>

                      {/* Sentiment badge */}
                      <span>
                        <span className={sentimentClass(review.sentiment)}>
                          {sentimentLabel(review.sentiment)}
                        </span>
                      </span>

                      {/* Score */}
                      <span
                        className="text-xs font-mono font-semibold"
                        style={{ color: scoreColor(review.sentiment_score) }}
                      >
                        {review.sentiment_score != null
                          ? `${review.sentiment_score >= 0 ? '+' : ''}${review.sentiment_score.toFixed(2)}`
                          : '—'}
                      </span>

                      {/* Status */}
                      <span
                        className="inline-block px-2 py-0.5 rounded-full text-xs capitalize"
                        style={{ background: ss.bg, color: ss.color, border: `1px solid ${ss.border}` }}
                      >
                        {review.processing_status}
                      </span>
                    </motion.div>
                  )
                })}
              </div>
            </>
          )}
        </div>

        {/* ── Pagination ─────────────────────────────────────────── */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
              Page {filters.page} of {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <button
                disabled={filters.page <= 1}
                onClick={() => updateFilter({ page: filters.page - 1 })}
                className="btn-ghost text-xs px-3 py-2 disabled:opacity-30"
              >
                <ChevronLeft size={14} />
                Prev
              </button>

              {/* Page numbers */}
              <div className="flex gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let p: number
                  if (totalPages <= 5) {
                    p = i + 1
                  } else if (filters.page <= 3) {
                    p = i + 1
                  } else if (filters.page >= totalPages - 2) {
                    p = totalPages - 4 + i
                  } else {
                    p = filters.page - 2 + i
                  }
                  return (
                    <button
                      key={p}
                      onClick={() => updateFilter({ page: p })}
                      className="w-8 h-8 rounded-lg text-xs font-medium transition-all duration-150"
                      style={
                        filters.page === p
                          ? { background: 'linear-gradient(135deg,#7c3aed,#2563eb)', color: '#fff' }
                          : { background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.5)' }
                      }
                    >
                      {p}
                    </button>
                  )
                })}
              </div>

              <button
                disabled={filters.page >= totalPages}
                onClick={() => updateFilter({ page: filters.page + 1 })}
                className="btn-ghost text-xs px-3 py-2 disabled:opacity-30"
              >
                Next
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Detail Drawer ──────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedId && (
          <ReviewDrawer
            reviewId={selectedId}
            onClose={() => setSelectedId(null)}
            userRole={user?.role ?? 'viewer'}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
