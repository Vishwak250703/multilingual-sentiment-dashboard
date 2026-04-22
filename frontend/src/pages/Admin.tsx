import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Users, Activity, Plus, Trash2, ChevronLeft, ChevronRight,
  CheckCircle2, XCircle, Shield, Eye, UserCog,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { TopBar } from '@/components/layout/TopBar'
import { adminApi } from '@/api/endpoints'
import { useAuthStore } from '@/store/authStore'
import type { User as UserType, AuditLog } from '@/types'

// ─── Helpers ──────────────────────────────────────────────────
function roleStyle(role: string) {
  switch (role) {
    case 'admin':   return { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.25)' }
    case 'analyst': return { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)',  border: 'rgba(96,165,250,0.25)'  }
    default:        return { color: '#94a3b8', bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.25)' }
  }
}

function roleIcon(role: string) {
  if (role === 'admin')   return Shield
  if (role === 'analyst') return UserCog
  return Eye
}

function actionColor(action: string) {
  if (action.includes('delete') || action.includes('remove')) return '#f87171'
  if (action.includes('login'))    return '#60a5fa'
  if (action.includes('upload'))   return '#a78bfa'
  if (action.includes('export'))   return '#4ade80'
  if (action.includes('update') || action.includes('correct')) return '#fbbf24'
  return '#94a3b8'
}

function formatDate(dt: string) {
  try { return format(new Date(dt), 'MMM d, yyyy HH:mm') } catch { return '—' }
}

const selectStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '0.625rem',
  color: 'rgba(255,255,255,0.85)',
  padding: '0.375rem 0.75rem',
  fontSize: '0.75rem',
  outline: 'none',
  cursor: 'pointer',
}

const inputStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '0.75rem',
  color: 'rgba(255,255,255,0.9)',
  padding: '0.5rem 0.875rem',
  fontSize: '0.8125rem',
  outline: 'none',
  width: '100%',
}

// ─── Users Panel ──────────────────────────────────────────────
function UsersPanel({ currentUserId, tenantId }: { currentUserId: string; tenantId: string }) {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [newUser, setNewUser] = useState({
    full_name: '', email: '', password: '', role: 'viewer',
  })

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: adminApi.listUsers,
  })

  const createMutation = useMutation({
    mutationFn: () => adminApi.createUser({ ...newUser, tenant_id: tenantId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setShowAddForm(false)
      setNewUser({ full_name: '', email: '', password: '', role: 'viewer' })
      toast.success('User created')
    },
    onError: (err: any) =>
      toast.error(err.response?.data?.detail ?? 'Failed to create user'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { role?: string; is_active?: boolean } }) =>
      adminApi.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User updated')
    },
    onError: () => toast.error('Failed to update user'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setDeleteConfirmId(null)
      toast.success('User deleted')
    },
    onError: (err: any) =>
      toast.error(err.response?.data?.detail ?? 'Failed to delete user'),
  })

  const handleCreate = () => {
    if (!newUser.full_name || !newUser.email || !newUser.password) {
      toast.error('Name, email and password are required')
      return
    }
    createMutation.mutate()
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
          {(users?.length ?? 0)} user{users?.length !== 1 ? 's' : ''} in this workspace
        </p>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="btn-primary text-xs px-3 py-2"
        >
          <Plus size={13} />
          Add User
        </button>
      </div>

      {/* Add user form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            className="glass-card p-5 space-y-4"
            style={{ borderColor: 'rgba(124,58,237,0.2)' }}
          >
            <p className="text-sm font-semibold text-white">New User</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Full Name</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser((u) => ({ ...u, full_name: e.target.value }))}
                  placeholder="Jane Smith"
                  style={inputStyle}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Email</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser((u) => ({ ...u, email: e.target.value }))}
                  placeholder="jane@company.com"
                  style={inputStyle}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Password</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser((u) => ({ ...u, password: e.target.value }))}
                  placeholder="Min 8 characters"
                  style={inputStyle}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser((u) => ({ ...u, role: e.target.value }))}
                  style={{ ...selectStyle, width: '100%', padding: '0.5rem 0.875rem' }}
                >
                  <option value="viewer">Viewer</option>
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="btn-primary text-xs px-4 py-2"
              >
                {createMutation.isPending
                  ? <span className="w-3 h-3 rounded-full border border-white/60 border-t-transparent animate-spin" />
                  : <Plus size={13} />
                }
                Create User
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false)
                  setNewUser({ full_name: '', email: '', password: '', role: 'viewer' })
                }}
                className="btn-ghost text-xs px-4 py-2"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Users table */}
      <div className="glass-card overflow-hidden">
        {/* Header */}
        <div
          className="grid px-5 py-3 text-xs font-semibold uppercase tracking-wider"
          style={{
            gridTemplateColumns: '1fr 160px 100px 120px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            color: 'rgba(255,255,255,0.35)',
          }}
        >
          <span>User</span>
          <span>Role</span>
          <span>Status</span>
          <span>Actions</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-5 h-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        ) : !users?.length ? (
          <div className="flex flex-col items-center gap-2 py-12">
            <Users size={20} style={{ color: 'rgba(255,255,255,0.2)' }} />
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>No users found</p>
          </div>
        ) : (
          users.map((u: UserType) => {
            const rs = roleStyle(u.role)
            const RoleIcon = roleIcon(u.role)
            const isMe = u.id === currentUserId
            const isDeleting = deleteConfirmId === u.id

            return (
              <motion.div
                key={u.id}
                layout
                className="grid items-center px-5 py-4"
                style={{
                  gridTemplateColumns: '1fr 160px 100px 120px',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                }}
              >
                {/* User info */}
                <div className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{ background: 'linear-gradient(135deg, #7c3aed, #2563eb)' }}
                  >
                    {u.full_name?.[0]?.toUpperCase() ?? 'U'}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white leading-tight">
                      {u.full_name}
                      {isMe && (
                        <span className="ml-1.5 text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>(you)</span>
                      )}
                    </p>
                    <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>{u.email}</p>
                  </div>
                </div>

                {/* Role selector */}
                <div>
                  <select
                    value={u.role}
                    disabled={isMe}
                    onChange={(e) =>
                      updateMutation.mutate({ id: u.id, data: { role: e.target.value } })
                    }
                    style={{
                      ...selectStyle,
                      background: rs.bg,
                      borderColor: rs.border,
                      color: rs.color,
                      opacity: isMe ? 0.5 : 1,
                    }}
                  >
                    <option value="viewer">Viewer</option>
                    <option value="analyst">Analyst</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                {/* Active toggle */}
                <div>
                  <button
                    disabled={isMe || updateMutation.isPending}
                    onClick={() =>
                      updateMutation.mutate({ id: u.id, data: { is_active: !u.is_active } })
                    }
                    className="flex items-center gap-1.5 text-xs font-medium transition-opacity"
                    style={{
                      color: u.is_active ? '#4ade80' : '#f87171',
                      opacity: isMe ? 0.4 : 1,
                    }}
                  >
                    {u.is_active
                      ? <CheckCircle2 size={14} />
                      : <XCircle size={14} />
                    }
                    {u.is_active ? 'Active' : 'Inactive'}
                  </button>
                </div>

                {/* Delete */}
                <div>
                  {isMe ? (
                    <span className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>—</span>
                  ) : isDeleting ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs" style={{ color: '#f87171' }}>Delete?</span>
                      <button
                        onClick={() => deleteMutation.mutate(u.id)}
                        disabled={deleteMutation.isPending}
                        className="text-xs font-semibold"
                        style={{ color: '#f87171' }}
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setDeleteConfirmId(null)}
                        className="text-xs"
                        style={{ color: 'rgba(255,255,255,0.4)' }}
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirmId(u.id)}
                      className="p-1.5 rounded-lg transition-all duration-150"
                      style={{ color: 'rgba(255,255,255,0.3)' }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.color = '#f87171'
                        e.currentTarget.style.background = 'rgba(248,113,113,0.08)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.color = 'rgba(255,255,255,0.3)'
                        e.currentTarget.style.background = 'transparent'
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </motion.div>
            )
          })
        )}
      </div>
    </div>
  )
}

// ─── Audit Logs Panel ─────────────────────────────────────────
function AuditPanel() {
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['audit-logs', page],
    queryFn: () => adminApi.listAuditLogs(page, 50),
    placeholderData: (prev) => prev,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  return (
    <div className="space-y-4">
      <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
        {total.toLocaleString()} total event{total !== 1 ? 's' : ''}
      </p>

      <div className="glass-card overflow-hidden">
        {/* Header */}
        <div
          className="grid px-5 py-3 text-xs font-semibold uppercase tracking-wider"
          style={{
            gridTemplateColumns: '160px 140px 130px 120px 1fr',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            color: 'rgba(255,255,255,0.35)',
          }}
        >
          <span>Time</span>
          <span>User</span>
          <span>Action</span>
          <span>Resource</span>
          <span>Details</span>
        </div>

        {isError ? (
          <div className="flex flex-col items-center gap-2 py-12">
            <p className="text-sm text-red-400">Failed to load audit logs</p>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-5 h-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12">
            <Activity size={20} style={{ color: 'rgba(255,255,255,0.2)' }} />
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>No audit events yet</p>
          </div>
        ) : (
          items.map((log: AuditLog, i: number) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.01 }}
              className="grid items-center px-5 py-3"
              style={{
                gridTemplateColumns: '160px 140px 130px 120px 1fr',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
              }}
            >
              {/* Time */}
              <span className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {formatDate(log.created_at)}
              </span>

              {/* User */}
              <div>
                {log.user_full_name ? (
                  <div>
                    <p className="text-xs font-medium text-white leading-tight truncate">
                      {log.user_full_name}
                    </p>
                    <p className="text-xs truncate" style={{ color: 'rgba(255,255,255,0.3)' }}>
                      {log.user_email}
                    </p>
                  </div>
                ) : (
                  <span className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>System</span>
                )}
              </div>

              {/* Action */}
              <span
                className="text-xs font-semibold capitalize"
                style={{ color: actionColor(log.action) }}
              >
                {log.action.replace(/_/g, ' ')}
              </span>

              {/* Resource */}
              <span className="text-xs capitalize" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {log.resource ?? '—'}
                {log.resource_id && (
                  <span className="block font-mono text-xs truncate" style={{ color: 'rgba(255,255,255,0.2)', fontSize: '10px' }}>
                    {log.resource_id.slice(0, 12)}…
                  </span>
                )}
              </span>

              {/* Extra */}
              <div className="flex flex-wrap gap-1.5">
                {log.ip_address && (
                  <span
                    className="px-1.5 py-0.5 rounded text-xs font-mono"
                    style={{ background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.3)', border: '1px solid rgba(255,255,255,0.07)' }}
                  >
                    {log.ip_address}
                  </span>
                )}
                {log.extra && Object.entries(log.extra).slice(0, 2).map(([k, v]) => (
                  <span
                    key={k}
                    className="px-1.5 py-0.5 rounded text-xs"
                    style={{ background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.35)', border: '1px solid rgba(255,255,255,0.07)' }}
                  >
                    {k}: {String(v).slice(0, 20)}
                  </span>
                ))}
              </div>
            </motion.div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
            Page {page} of {totalPages} · {total} events
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="btn-ghost text-xs px-3 py-2 disabled:opacity-30"
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="btn-ghost text-xs px-3 py-2 disabled:opacity-30"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────
export default function Admin() {
  const { user } = useAuthStore()
  const [tab, setTab] = useState<'users' | 'audit'>('users')

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Admin" subtitle="Users, roles and audit logs" />

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Tabs */}
        <div
          className="flex gap-1 p-1 rounded-xl w-fit"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          {([
            { id: 'users', label: 'Users', icon: Users },
            { id: 'audit', label: 'Audit Logs', icon: Activity },
          ] as const).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
              style={
                tab === id
                  ? { background: 'linear-gradient(135deg,#7c3aed,#2563eb)', color: '#fff' }
                  : { color: 'rgba(255,255,255,0.45)' }
              }
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>

        {/* Panel content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            {tab === 'users' ? (
              <UsersPanel
                currentUserId={user?.id ?? ''}
                tenantId={user?.tenant_id ?? ''}
              />
            ) : (
              <AuditPanel />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
