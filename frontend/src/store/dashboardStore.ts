import { create } from 'zustand'

interface DashboardFilters {
  period: '1d' | '7d' | '30d' | '90d'
  product_id?: string
  branch_id?: string
  source?: string
}

interface DashboardState {
  filters: DashboardFilters
  isChatOpen: boolean
  liveNewReviews: number
  setFilters: (filters: Partial<DashboardFilters>) => void
  toggleChat: () => void
  setChatOpen: (open: boolean) => void
  incrementLiveReviews: (count?: number) => void
  resetLiveReviews: () => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  filters: { period: '7d' },
  isChatOpen: false,
  liveNewReviews: 0,

  setFilters: (filters) =>
    set((state) => ({ filters: { ...state.filters, ...filters } })),

  toggleChat: () =>
    set((state) => ({ isChatOpen: !state.isChatOpen })),

  setChatOpen: (open) => set({ isChatOpen: open }),

  incrementLiveReviews: (count = 1) =>
    set((state) => ({ liveNewReviews: state.liveNewReviews + count })),

  resetLiveReviews: () => set({ liveNewReviews: 0 }),
}))
