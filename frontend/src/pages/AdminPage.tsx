/**
 * AdminPage — панель администратора CHM_KRYPTON.
 * Доступна по /admin, требует admin/super_admin роли.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { apiClient } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import { LockIcon, SettingsIcon, UsersIcon, BarChartIcon, TargetIcon, ZapIcon, DiamondIcon, ClockIcon, AlertIcon, CheckCircleIcon } from '@/components/ui/Icon'

type AdminTab = 'overview' | 'users' | 'challenges' | 'payouts'

// ── Admin API helpers ────────────────────────────────────────────────────────

async function adminGet<T>(url: string, params?: object): Promise<T> {
  const resp = await apiClient.get<{ data: T }>(url, { params })
  return resp.data.data
}

async function adminPost<T>(url: string, body?: object): Promise<T> {
  const resp = await apiClient.post<{ data: T }>(url, body)
  return resp.data.data
}

async function adminPatch<T>(url: string, body?: object): Promise<T> {
  const resp = await apiClient.patch<{ data: T }>(url, body)
  return resp.data.data
}

// ── Types ────────────────────────────────────────────────────────────────────

interface AdminOverview {
  total_users: number
  active_users_today: number
  total_challenges: number
  active_challenges: number
  funded_accounts: number
  total_pnl_all: number
  pending_payouts: number
  pending_payout_amount: number
  master_balance: number
}

interface AdminUser {
  id: number
  telegram_id: number
  username?: string
  first_name: string
  role: string
  is_blocked: boolean
  active_challenges: number
  streak_days: number
  created_at: string
}

interface AdminChallenge {
  id: number
  user_id: number
  username?: string
  challenge_type_name: string
  account_size: number
  status: string
  phase?: number
  account_mode: string
  total_pnl: number
  daily_pnl: number
  trading_days_count: number
  started_at?: string
  failed_reason?: string
}

interface AdminPayout {
  id: number
  user_id: number
  username?: string
  challenge_id: number
  amount: number
  wallet_address: string
  network: string
  status: string
  requested_at: string
}

// ── Components ───────────────────────────────────────────────────────────────

export function AdminPage() {
  const role = useAuthStore((s) => s.role)
  const [tab, setTab] = useState<AdminTab>('overview')

  if (role !== 'admin' && role !== 'super_admin') {
    return (
      <div className="flex flex-col items-center justify-center min-h-dvh gap-4 px-8 text-center bg-bg-primary">
        <LockIcon size={64} color="#FF4757" />
        <h2 className="text-2xl font-bold text-white">Доступ запрещён</h2>
        <p className="text-text-secondary">Только администраторы могут открыть эту страницу.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-dvh bg-bg-primary pb-6">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-bg-border">
        <div className="flex items-center gap-3">
          <SettingsIcon size={28} color="#6C63FF" />
          <div>
            <h1 className="text-xl font-bold text-white">CHM_KRYPTON Admin</h1>
            <p className="text-text-muted text-xs">{role === 'super_admin' ? 'Super Admin' : 'Admin'}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 mt-4 flex gap-1 p-1 bg-bg-border rounded-xl mx-4">
        {(['overview', 'users', 'challenges', 'payouts'] as AdminTab[]).map((t) => (
          <button
            key={t}
            className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: tab === t ? '#12121A' : 'transparent',
              color: tab === t ? '#fff' : '#4A4A5A',
            }}
            onClick={() => setTab(t)}
          >
            {t === 'overview' ? <span className="flex items-center justify-center gap-1"><BarChartIcon size={12} /> Обзор</span>
              : t === 'users' ? <span className="flex items-center justify-center gap-1"><UsersIcon size={12} /> Польз.</span>
              : t === 'challenges' ? <span className="flex items-center justify-center gap-1"><TargetIcon size={12} /> Испыт.</span>
              : <span className="flex items-center justify-center gap-1"><DiamondIcon size={12} /> Выплаты</span>}
          </button>
        ))}
      </div>

      <div className="mt-4 px-4">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'users' && <UsersTab />}
        {tab === 'challenges' && <ChallengesTab />}
        {tab === 'payouts' && <PayoutsTab />}
      </div>
    </div>
  )
}

// ── Overview ─────────────────────────────────────────────────────────────────

function OverviewTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-overview'],
    queryFn: () => adminGet<AdminOverview>('/api/v1/admin/overview'),
    refetchInterval: 30_000,
  })

  if (isLoading) return <p className="text-text-muted text-center py-8">Загрузка...</p>
  if (!data) return null

  const stats = [
    { label: 'Пользователей', value: data.total_users, icon: <UsersIcon size={16} color="#6C63FF" />, color: '#6C63FF' },
    { label: 'Активных сегодня', value: data.active_users_today, icon: <CheckCircleIcon size={16} color="#00D4AA" />, color: '#00D4AA' },
    { label: 'Всего испытаний', value: data.total_challenges, icon: <TargetIcon size={16} color="#FFA502" />, color: '#FFA502' },
    { label: 'Активных испытаний', value: data.active_challenges, icon: <ZapIcon size={16} color="#FFA502" />, color: '#FFA502' },
    { label: 'Funded аккаунтов', value: data.funded_accounts, icon: <DiamondIcon size={16} color="#00D4AA" />, color: '#00D4AA' },
    { label: 'Выплат на рассмотрении', value: data.pending_payouts, icon: <ClockIcon size={16} color="#FF4757" />, color: '#FF4757' },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {stats.map((s) => (
          <motion.div
            key={s.label}
            className="glass-card p-4"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="flex items-center gap-2 mb-1">
              <span>{s.icon}</span>
              <span className="text-xs text-text-secondary">{s.label}</span>
            </div>
            <p className="num text-2xl font-bold" style={{ color: s.color }}>
              {s.value.toLocaleString('en')}
            </p>
          </motion.div>
        ))}
      </div>

      {/* Financials */}
      <div className="glass-card p-4 space-y-3">
        <p className="text-sm font-semibold text-white">Финансы</p>
        <FinRow label="Общий PnL всех трейдеров" value={`$${data.total_pnl_all.toFixed(2)}`} color="#00D4AA" />
        <FinRow label="Сумма к выплате (pending)" value={`$${data.pending_payout_amount.toFixed(2)}`} color="#FFA502" />
        <FinRow label="Баланс Master аккаунта" value={`$${data.master_balance.toFixed(2)}`}
          color={data.master_balance < 10000 ? '#FF4757' : '#00D4AA'} />
      </div>
    </div>
  )
}

function FinRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="num font-bold" style={{ color }}>{value}</span>
    </div>
  )
}

// ── Users ─────────────────────────────────────────────────────────────────────

function UsersTab() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page, search],
    queryFn: () => adminGet<{ users: AdminUser[]; total: number }>('/api/v1/admin/users', {
      limit,
      offset: page * limit,
      search: search || undefined,
    }),
    staleTime: 10_000,
  })

  const blockMutation = useMutation({
    mutationFn: ({ userId, block }: { userId: number; block: boolean }) =>
      adminPost(`/api/v1/admin/users/${userId}/${block ? 'block' : 'unblock'}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  return (
    <div className="space-y-3">
      <input
        type="text"
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(0) }}
        placeholder="Поиск по username..."
        className="w-full bg-bg-border border border-bg-border rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none"
      />

      {isLoading ? (
        <p className="text-text-muted text-center py-8">Загрузка...</p>
      ) : (
        <>
          <p className="text-xs text-text-muted">Всего: {data?.total ?? 0}</p>
          <div className="space-y-2">
            {(data?.users ?? []).map((user) => (
              <div key={user.id} className="glass-card p-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-white truncate">
                      {user.username ? `@${user.username}` : user.first_name}
                    </p>
                    <RoleBadge role={user.role} />
                    {user.is_blocked && (
                      <span className="text-xs text-loss flex items-center gap-1"><LockIcon size={11} color="#FF4757" /> Заблокирован</span>
                    )}
                  </div>
                  <p className="text-xs text-text-muted num">
                    ID: {user.telegram_id} · Испытаний: {user.active_challenges} · Стрик: {user.streak_days}д
                  </p>
                </div>
                <button
                  className="shrink-0 px-2 py-1 rounded-lg text-xs font-semibold"
                  style={{
                    background: user.is_blocked ? 'rgba(0,212,170,0.1)' : 'rgba(255,71,87,0.1)',
                    color: user.is_blocked ? '#00D4AA' : '#FF4757',
                  }}
                  onClick={() => blockMutation.mutate({ userId: user.id, block: !user.is_blocked })}
                >
                  {user.is_blocked ? 'Разблокировать' : 'Заблокировать'}
                </button>
              </div>
            ))}
          </div>
          <Pagination
            page={page}
            total={data?.total ?? 0}
            limit={limit}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}

// ── Challenges ────────────────────────────────────────────────────────────────

function ChallengesTab() {
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['admin-challenges', page, statusFilter],
    queryFn: () => adminGet<{ challenges: AdminChallenge[]; total: number }>('/api/v1/admin/challenges', {
      limit,
      offset: page * limit,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
    staleTime: 10_000,
  })

  const STATUS_OPTS = ['all', 'phase1', 'phase2', 'funded', 'failed', 'completed']
  const STATUS_COLORS: Record<string, string> = {
    phase1: '#6C63FF', phase2: '#FFA502', funded: '#00D4AA',
    failed: '#FF4757', completed: '#00D4AA',
  }

  return (
    <div className="space-y-3">
      {/* Status filter pills */}
      <div className="flex gap-1 flex-wrap">
        {STATUS_OPTS.map((s) => (
          <button
            key={s}
            className="px-3 py-1 rounded-full text-xs font-semibold transition-all"
            style={{
              background: statusFilter === s ? '#6C63FF20' : '#1E1E2E',
              color: statusFilter === s ? '#6C63FF' : '#4A4A5A',
              border: statusFilter === s ? '1px solid #6C63FF40' : '1px solid transparent',
            }}
            onClick={() => { setStatusFilter(s); setPage(0) }}
          >
            {s}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-text-muted text-center py-8">Загрузка...</p>
      ) : (
        <>
          <p className="text-xs text-text-muted">Всего: {data?.total ?? 0}</p>
          <div className="space-y-2">
            {(data?.challenges ?? []).map((ch) => (
              <div key={ch.id} className="glass-card p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">
                      {ch.username ? `@${ch.username}` : `User #${ch.user_id}`}
                    </span>
                    <span
                      className="text-xs px-2 py-0.5 rounded font-bold"
                      style={{
                        background: `${STATUS_COLORS[ch.status] ?? '#6C63FF'}20`,
                        color: STATUS_COLORS[ch.status] ?? '#6C63FF',
                      }}
                    >
                      {ch.status}
                    </span>
                  </div>
                  <span className="num text-sm font-bold" style={{ color: ch.total_pnl >= 0 ? '#00D4AA' : '#FF4757' }}>
                    {ch.total_pnl >= 0 ? '+' : ''}{ch.total_pnl.toFixed(2)}
                  </span>
                </div>
                <p className="text-xs text-text-muted num">
                  {ch.challenge_type_name} · ${ch.account_size.toLocaleString('en')}
                  · {ch.account_mode} · {ch.trading_days_count}д
                </p>
                {ch.failed_reason && (
                  <p className="text-xs text-loss mt-1 flex items-center gap-1"><AlertIcon size={12} color="#FF4757" /> {ch.failed_reason}</p>
                )}
              </div>
            ))}
          </div>
          <Pagination page={page} total={data?.total ?? 0} limit={limit} onPage={setPage} />
        </>
      )}
    </div>
  )
}

// ── Payouts ──────────────────────────────────────────────────────────────────

function PayoutsTab() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('pending')

  const { data: payouts = [], isLoading } = useQuery({
    queryKey: ['admin-payouts', statusFilter],
    queryFn: () => adminGet<AdminPayout[]>('/api/v1/admin/payouts', {
      status: statusFilter !== 'all' ? statusFilter : undefined,
      limit: 50,
    }),
    refetchInterval: 30_000,
  })

  const approveMutation = useMutation({
    mutationFn: (payoutId: number) =>
      adminPost(`/api/v1/admin/payouts/${payoutId}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-payouts'] }),
  })

  const rejectMutation = useMutation({
    mutationFn: (payoutId: number) =>
      adminPost(`/api/v1/admin/payouts/${payoutId}/reject`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-payouts'] }),
  })

  return (
    <div className="space-y-3">
      <div className="flex gap-1">
        {['pending', 'approved', 'rejected', 'all'].map((s) => (
          <button
            key={s}
            className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: statusFilter === s ? '#12121A' : 'transparent',
              color: statusFilter === s ? '#fff' : '#4A4A5A',
            }}
            onClick={() => setStatusFilter(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-text-muted text-center py-8">Загрузка...</p>
      ) : payouts.length === 0 ? (
        <p className="text-center text-text-muted py-8">Нет выплат</p>
      ) : (
        <div className="space-y-2">
          {payouts.map((p) => (
            <div key={p.id} className="glass-card p-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-semibold text-white">
                    {p.username ? `@${p.username}` : `User #${p.user_id}`}
                  </p>
                  <p className="num text-xs text-text-muted">
                    {p.network} · Challenge #{p.challenge_id}
                  </p>
                </div>
                <p className="num text-lg font-bold text-profit">${p.amount.toFixed(2)}</p>
              </div>
              <p className="num text-xs text-text-muted mb-2 break-all">{p.wallet_address}</p>
              {p.status === 'pending' && (
                <div className="flex gap-2">
                  <button
                    className="flex-1 py-1.5 rounded-lg text-xs font-bold"
                    style={{ background: 'rgba(0,212,170,0.15)', color: '#00D4AA' }}
                    onClick={() => approveMutation.mutate(p.id)}
                    disabled={approveMutation.isPending}
                  >
                    <span className="flex items-center justify-center gap-1"><CheckCircleIcon size={14} color="#00D4AA" /> Одобрить</span>
                  </button>
                  <button
                    className="flex-1 py-1.5 rounded-lg text-xs font-bold"
                    style={{ background: 'rgba(255,71,87,0.15)', color: '#FF4757' }}
                    onClick={() => rejectMutation.mutate(p.id)}
                    disabled={rejectMutation.isPending}
                  >
                    <span className="flex items-center justify-center gap-1"><AlertIcon size={14} color="#FF4757" /> Отклонить</span>
                  </button>
                </div>
              )}
              {p.status !== 'pending' && (
                <p className="text-xs font-semibold"
                  style={{ color: p.status === 'approved' ? '#00D4AA' : '#FF4757' }}>
                  {p.status === 'approved' ? <span className="flex items-center gap-1"><CheckCircleIcon size={12} color="#00D4AA" /> Одобрено</span> : <span className="flex items-center gap-1"><AlertIcon size={12} color="#FF4757" /> Отклонено</span>}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Shared components ─────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  const config: Record<string, { label: string; color: string }> = {
    super_admin: { label: 'SUPER', color: '#FF4757' },
    admin: { label: 'ADMIN', color: '#FFA502' },
    funded_trader: { label: 'FUNDED', color: '#00D4AA' },
    challenger: { label: 'TRADER', color: '#6C63FF' },
    elite_trader: { label: 'ELITE', color: '#FFD700' },
  }
  const c = config[role]
  if (!c) return null
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded font-bold"
      style={{ background: `${c.color}20`, color: c.color }}>
      {c.label}
    </span>
  )
}

function Pagination({ page, total, limit, onPage }: {
  page: number; total: number; limit: number; onPage: (p: number) => void
}) {
  const maxPage = Math.ceil(total / limit) - 1
  if (maxPage <= 0) return null
  return (
    <div className="flex items-center justify-between">
      <button
        className="px-4 py-2 rounded-xl text-sm text-text-secondary disabled:opacity-30"
        style={{ background: '#1E1E2E' }}
        onClick={() => onPage(page - 1)}
        disabled={page === 0}
      >
        ← Назад
      </button>
      <span className="text-xs text-text-muted">
        {page + 1} / {maxPage + 1}
      </span>
      <button
        className="px-4 py-2 rounded-xl text-sm text-text-secondary disabled:opacity-30"
        style={{ background: '#1E1E2E' }}
        onClick={() => onPage(page + 1)}
        disabled={page >= maxPage}
      >
        Вперёд →
      </button>
    </div>
  )
}
