import { apiClient } from './client'
import type {
  TokenResponse, User, DashboardData, KPIData, SentimentTrend,
  ReviewPaginated, Review, AlertListResponse, ChatRequest, ChatResponse,
  UploadJobStatus, InsightItem, AspectSentiment, ChatMessage,
  AuditLogPaginated,
} from '@/types'

// ─── Auth ──────────────────────────────────────────────────────
export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const form = new FormData()
    form.append('username', email)
    form.append('password', password)
    const res = await apiClient.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return res.data
  },

  me: async (): Promise<User> => {
    const res = await apiClient.get('/auth/me')
    return res.data
  },

  refresh: async (refresh_token: string): Promise<TokenResponse> => {
    const res = await apiClient.post('/auth/refresh', { refresh_token })
    return res.data
  },

  logout: async () => {
    await apiClient.post('/auth/logout')
    localStorage.clear()
  },
}

// ─── Dashboard ─────────────────────────────────────────────────
export const dashboardApi = {
  getDashboard: async (period = '7d'): Promise<DashboardData> => {
    const res = await apiClient.get('/dashboard/', { params: { period } })
    return res.data
  },

  getKPIs: async (period = '7d'): Promise<KPIData> => {
    const res = await apiClient.get('/dashboard/kpis', { params: { period } })
    return res.data
  },

  getTrend: async (period = '7d', granularity = 'daily'): Promise<SentimentTrend> => {
    const res = await apiClient.get('/dashboard/trend', { params: { period, granularity } })
    return res.data
  },
}

// ─── Reviews ──────────────────────────────────────────────────
export const reviewsApi = {
  list: async (params: Record<string, unknown> = {}): Promise<ReviewPaginated> => {
    const res = await apiClient.get('/reviews/', { params })
    return res.data
  },

  get: async (id: string): Promise<Review> => {
    const res = await apiClient.get(`/reviews/${id}`)
    return res.data
  },

  correct: async (id: string, body: { corrected_sentiment: string; note?: string }) => {
    const res = await apiClient.post(`/reviews/${id}/correct`, body)
    return res.data
  },

  exportCsv: async (params: Record<string, unknown> = {}): Promise<void> => {
    const res = await apiClient.get('/reviews/export', {
      params,
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `reviews_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },

  exportPdf: async (params: Record<string, unknown> = {}): Promise<void> => {
    const res = await apiClient.get('/reviews/export/pdf', {
      params,
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `sentiment_report_${new Date().toISOString().slice(0, 10)}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },
}

// ─── Alerts ───────────────────────────────────────────────────
export const alertsApi = {
  list: async (resolved = false): Promise<AlertListResponse> => {
    const res = await apiClient.get('/alerts/', { params: { resolved } })
    return res.data
  },

  resolve: async (id: string) => {
    const res = await apiClient.post(`/alerts/${id}/resolve`)
    return res.data
  },
}

// ─── Insights ─────────────────────────────────────────────────
export const insightsApi = {
  getInsights: async (period = '7d'): Promise<InsightItem[]> => {
    const res = await apiClient.get('/insights/', { params: { period } })
    return res.data
  },

  getAspects: async (period = '7d'): Promise<AspectSentiment[]> => {
    const res = await apiClient.get('/insights/aspects', { params: { period } })
    return res.data
  },
}

// ─── Chat ─────────────────────────────────────────────────────
export const chatApi = {
  ask: async (question: string, history: ChatMessage[] = []): Promise<ChatResponse> => {
    const res = await apiClient.post('/chat/ask', {
      question,
      conversation_history: history,
    })
    return res.data
  },
}

// ─── Ingest ───────────────────────────────────────────────────
export const ingestApi = {
  uploadFile: async (file: File): Promise<UploadJobStatus> => {
    const form = new FormData()
    form.append('file', file)
    const res = await apiClient.post('/ingest/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  getJobStatus: async (jobId: string): Promise<UploadJobStatus> => {
    const res = await apiClient.get(`/ingest/job/${jobId}`)
    return res.data
  },
}

// ─── Admin ────────────────────────────────────────────────────
export const adminApi = {
  listUsers: async () => {
    const res = await apiClient.get('/admin/users')
    return res.data
  },

  createUser: async (data: { email: string; full_name: string; password: string; role: string; tenant_id: string }) => {
    const res = await apiClient.post('/admin/users', data)
    return res.data
  },

  updateUser: async (id: string, data: Partial<{ full_name: string; role: string; is_active: boolean }>) => {
    const res = await apiClient.patch(`/admin/users/${id}`, data)
    return res.data
  },

  deleteUser: async (id: string) => {
    await apiClient.delete(`/admin/users/${id}`)
  },

  listAuditLogs: async (page = 1, page_size = 50): Promise<AuditLogPaginated> => {
    const res = await apiClient.get('/admin/audit-logs', { params: { page, page_size } })
    return res.data
  },
}
