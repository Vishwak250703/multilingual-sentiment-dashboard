import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

export function formatPercent(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`
}

export function formatScore(n: number): string {
  return n.toFixed(2)
}

export function sentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'positive': return '#4ade80'
    case 'negative': return '#f87171'
    default:         return '#94a3b8'
  }
}

export function sentimentBgClass(sentiment: string): string {
  switch (sentiment) {
    case 'positive': return 'badge-positive'
    case 'negative': return 'badge-negative'
    default:         return 'badge-neutral'
  }
}

export function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return '#f87171'
    case 'high':     return '#fb923c'
    case 'medium':   return '#fbbf24'
    default:         return '#60a5fa'
  }
}

export function getLanguageName(code: string): string {
  const map: Record<string, string> = {
    en: 'English', hi: 'Hindi', te: 'Telugu', ta: 'Tamil',
    kn: 'Kannada', mr: 'Marathi', bn: 'Bengali', gu: 'Gujarati',
    ur: 'Urdu', ar: 'Arabic', fr: 'French', de: 'German',
    es: 'Spanish', pt: 'Portuguese', ja: 'Japanese', zh: 'Chinese',
  }
  return map[code] ?? code.toUpperCase()
}
