// ─── Auth ──────────────────────────────────────────────────────
export interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'analyst' | 'viewer'
  tenant_id: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// ─── Review ────────────────────────────────────────────────────
export interface SentenceSentiment {
  sentence: string
  sentiment: Sentiment
  score: number
}

export interface Review {
  id: string
  tenant_id: string
  raw_text: string
  translated_text?: string
  original_language: string
  detected_language?: string
  source: string
  product_id?: string
  branch_id?: string
  sentiment?: Sentiment
  sentiment_score?: number
  confidence?: number
  sentence_sentiments?: SentenceSentiment[]
  aspects?: Record<string, string>
  keywords?: string[]
  is_pii_masked: boolean
  processing_status: ProcessingStatus
  review_date?: string
  created_at: string
  processed_at?: string
}

export type Sentiment = 'positive' | 'negative' | 'neutral'
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ReviewPaginated {
  items: Review[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ─── Dashboard ────────────────────────────────────────────────
export interface KPIData {
  total_reviews: number
  overall_sentiment_score: number
  positive_percent: number
  negative_percent: number
  neutral_percent: number
  active_languages: number
  change_from_last_period?: Record<string, number>
}

export interface TrendPoint {
  date: string
  sentiment_score: number
  positive_count: number
  negative_count: number
  neutral_count: number
  total: number
}

export interface SentimentTrend {
  points: TrendPoint[]
  period: string
}

export interface LanguageDistribution {
  language: string
  language_name: string
  count: number
  percent: number
}

export interface SourceBreakdown {
  source: string
  count: number
  percent: number
  sentiment_score: number
}

export interface AspectSentiment {
  aspect: string
  sentiment: Sentiment
  score: number
  count: number
}

export interface InsightItem {
  type: 'trend' | 'spike' | 'keyword' | 'aspect'
  title: string
  description: string
  severity: 'info' | 'warning' | 'critical'
  metadata?: Record<string, unknown>
}

export interface DashboardData {
  kpis: KPIData
  trend: SentimentTrend
  language_distribution: LanguageDistribution[]
  source_breakdown: SourceBreakdown[]
  aspect_sentiments: AspectSentiment[]
  top_keywords: Array<{ keyword: string; count: number; sentiment: Sentiment }>
  insights: InsightItem[]
}

// ─── Alert ────────────────────────────────────────────────────
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical'
export type AlertType = 'sentiment_drop' | 'complaint_spike' | 'product_alert' | 'branch_alert' | 'anomaly'

export interface Alert {
  id: string
  tenant_id: string
  alert_type: AlertType
  severity: AlertSeverity
  title: string
  message: string
  metadata?: Record<string, unknown>
  is_resolved: boolean
  triggered_at: string
  resolved_at?: string
}

export interface AlertListResponse {
  items: Alert[]
  unresolved_count: number
  total: number
}

// ─── Audit Log ────────────────────────────────────────────────
export interface AuditLog {
  id: string
  user_id?: string
  user_email?: string
  user_full_name?: string
  action: string
  resource?: string
  resource_id?: string
  ip_address?: string
  extra?: Record<string, unknown>
  created_at: string
}

export interface AuditLogPaginated {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ─── Chat ─────────────────────────────────────────────────────
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  question: string
  conversation_history: ChatMessage[]
}

export interface ChartData {
  chart_type: 'line' | 'bar' | 'pie'
  title: string
  data: Array<Record<string, unknown>>
  x_key?: string
  y_key?: string
}

export interface ChatResponse {
  answer: string
  chart?: ChartData
  supporting_reviews?: Array<Record<string, unknown>>
  confidence?: number
}

// ─── Upload ───────────────────────────────────────────────────
export interface UploadJobStatus {
  job_id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  total_rows?: number
  processed_rows?: number
  failed_rows?: number
  error_message?: string
  progress_percent?: number
}
