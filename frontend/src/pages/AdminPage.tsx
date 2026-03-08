/**
 * AdminPage — панель администратора CHM KRYPTON.
 * Доступна по /admin, требует admin/super_admin роли.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { apiClient } from '@/api/client'
import { useAuthStore } from '@/store/authStore'

type AdminTab = 'testing' | 'overview' | 'users' | 'challenges' | 'payouts'

// ── Admin API helpers ─────────────────────────────────────────────────────────

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

// ── Types ─────────────────────────────────────────────────────────────────────

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

interface ChallengeType {
  id: number
  name: string
  account_size: number
  price: number
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function AdminPage() {
  const role = useAuthStore((s) => s.role)
  const userId = useAuthStore((s) => s.userId)
  const [tab, setTab] = useState<AdminTab>('testing')
  const [bootstrapStatus, setBootstrapStatus] = useState('')
  const [bootstrapping, setBootstrapping] = useState(false)

  // Если не админ — показываем bootstrap-панель
  if (role !== 'admin' && role !== 'super_admin') {
    const PRESET_IDS = [705020259, 445677777]

    const doBootstrap = async (tgId: number) => {
      setBootstrapping(true)
      setBootstrapStatus('')
      try {
        const resp = await apiClient.post<{ data: { role: string } }>(
          '/admin/bootstrap',
          { telegram_id: tgId }
        )
        setBootstrapStatus(`✅ Выдана роль: ${resp.data.data.role}. Перезагрузите страницу.`)
      } catch (e: any) {
        const msg = e?.response?.data?.detail ?? e?.message ?? 'Ошибка'
        setBootstrapStatus(`❌ ${msg}`)
      } finally {
        setBootstrapping(false)
      }
    }

    return (
      <div className="flex flex-col items-center justify-center min-h-dvh gap-6 px-8 text-center bg-bg-primary">
        <span className="text-6xl">🔒</span>
        <h2 className="text-2xl font-bold text-white">Доступ запрещён</h2>
        <p className="text-text-secondary text-sm">Только администраторы могут открыть эту страницу.</p>

        <div className="w-full max-w-sm space-y-3">
          <p className="text-xs text-text-muted">Bootstrap (разрешённые Telegram ID):</p>
          {PRESET_IDS.map((id) => (
            <button
              key={id}
              className="w-full py-3 rounded-xl text-sm font-bold"
              style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
              onClick={() => doBootstrap(id)}
              disabled={bootstrapping}
            >
              {bootstrapping ? '...' : `🚀 Выдать super_admin → TG ID ${id}`}
            </button>
          ))}
          {bootstrapStatus && (
            <p className="text-sm text-center" style={{
              color: bootstrapStatus.startsWith('✅') ? '#00D4AA' : '#FF4757'
            }}>
              {bootstrapStatus}
            </p>
          )}
          <p className="text-xs text-text-muted mt-4">
            Ваш ID: <span className="num text-white">{userId ?? '—'}</span>
          </p>
        </div>
      </div>
    )
  }

  const TABS: { key: AdminTab; label: string }[] = [
    { key: 'testing', label: '🧪 Тест' },
    { key: 'overview', label: '📊 Обзор' },
    { key: 'users', label: '👥 Юзеры' },
    { key: 'challenges', label: '🎯 Испытания' },
    { key: 'payouts', label: '💰 Выплаты' },
  ]

  return (
    <div className="flex flex-col min-h-dvh bg-bg-primary pb-6">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-bg-border">
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚙️</span>
          <div>
            <h1 className="text-xl font-bold text-white">CHM KRYPTON Admin</h1>
            <p className="text-text-muted text-xs">{role === 'super_admin' ? 'Super Admin' : 'Admin'}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 mt-4 flex gap-1 bg-bg-border rounded-xl mx-4 p-1 overflow-x-auto">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            className="flex-shrink-0 px-3 py-2 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: tab === key ? '#12121A' : 'transparent',
              color: tab === key ? '#fff' : '#4A4A5A',
            }}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-4 px-4">
        {tab === 'testing'    && <TestingTab />}
        {tab === 'overview'   && <OverviewTab />}
        {tab === 'users'      && <UsersTab />}
        {tab === 'challenges' && <ChallengesTab />}
        {tab === 'payouts'    && <PayoutsTab />}
      </div>
    </div>
  )
}

// ── 🧪 Testing Tab ────────────────────────────────────────────────────────────

function TestingTab() {
  const [tgInput, setTgInput] = useState('')
  const [foundUser, setFoundUser] = useState<AdminUser | null>(null)
  const [userError, setUserError] = useState('')
  const [userChallenges, setUserChallenges] = useState<AdminChallenge[]>([])
  const [selectedChallenge, setSelectedChallenge] = useState<AdminChallenge | null>(null)
  const [actionMsg, setActionMsg] = useState('')
  const [customPnl, setCustomPnl] = useState('')
  const [loading, setLoading] = useState(false)

  const PRESET_IDS = [705020259, 445677777]

  const msg = (text: string, isError = false) => {
    setActionMsg((isError ? '❌ ' : '✅ ') + text)
    setTimeout(() => setActionMsg(''), 4000)
  }

  // 1. Найти пользователя
  const findUser = async (tgId: number) => {
    setLoading(true)
    setUserError('')
    setFoundUser(null)
    setUserChallenges([])
    setSelectedChallenge(null)
    try {
      const user = await adminGet<AdminUser>(`/admin/users/by-tgid/${tgId}`)
      setFoundUser(user)
      // Сразу загружаем испытания
      const challenges = await adminGet<AdminChallenge[]>(`/admin/users/${user.id}/challenges`)
      setUserChallenges(challenges)
      if (challenges.length > 0) setSelectedChallenge(challenges[0])
    } catch (e: any) {
      setUserError(e?.response?.data?.detail ?? 'Пользователь не найден')
    } finally {
      setLoading(false)
    }
  }

  // 2. Изменить роль
  const setRole = async (role: string) => {
    if (!foundUser) return
    setLoading(true)
    try {
      await adminPost(`/admin/users/${foundUser.id}/set-role`, { role })
      setFoundUser({ ...foundUser, role })
      msg(`Роль изменена → ${role}`)
    } catch (e: any) {
      msg(e?.response?.data?.detail ?? 'Ошибка', true)
    } finally { setLoading(false) }
  }

  // 3. Выдать испытание
  const grantChallenge = async (ctId: number, ctName: string) => {
    if (!foundUser) return
    setLoading(true)
    try {
      const res = await adminPost<{ challenge_id: number; account_size: number }>(
        '/admin/challenges/grant',
        { user_id: foundUser.id, challenge_type_id: ctId }
      )
      msg(`Испытание #${res.challenge_id} выдано ($${res.account_size})`)
      // Обновим список
      const challenges = await adminGet<AdminChallenge[]>(`/admin/users/${foundUser.id}/challenges`)
      setUserChallenges(challenges)
      setSelectedChallenge(challenges[0] ?? null)
    } catch (e: any) {
      msg(e?.response?.data?.detail ?? 'Ошибка', true)
    } finally { setLoading(false) }
  }

  // 4. Force status
  const forceStatus = async (status: string, resetPnl = false) => {
    if (!selectedChallenge) return
    setLoading(true)
    try {
      await adminPost(`/admin/challenges/${selectedChallenge.id}/force-status`, { status, reset_pnl: resetPnl })
      const updated = { ...selectedChallenge, status }
      setSelectedChallenge(updated)
      setUserChallenges(prev => prev.map(c => c.id === updated.id ? updated : c))
      msg(`Статус → ${status}${resetPnl ? ' + PnL сброшен' : ''}`)
    } catch (e: any) {
      msg(e?.response?.data?.detail ?? 'Ошибка', true)
    } finally { setLoading(false) }
  }

  // 5. Добавить PnL
  const addPnl = async (amount: number, addDay = true) => {
    if (!selectedChallenge) return
    setLoading(true)
    try {
      const res = await adminPost<{ total_pnl: number; trading_days_count: number }>(
        `/admin/challenges/${selectedChallenge.id}/add-pnl`,
        { amount, add_day: addDay }
      )
      const updated = { ...selectedChallenge, total_pnl: res.total_pnl, trading_days_count: res.trading_days_count }
      setSelectedChallenge(updated)
      setUserChallenges(prev => prev.map(c => c.id === updated.id ? updated : c))
      msg(`PnL ${amount > 0 ? '+' : ''}${amount} → итого $${res.total_pnl.toFixed(2)}, дней: ${res.trading_days_count}`)
    } catch (e: any) {
      msg(e?.response?.data?.detail ?? 'Ошибка', true)
    } finally { setLoading(false) }
  }

  // Данные типов испытаний
  const { data: challengeTypes = [] } = useQuery({
    queryKey: ['challenge-types'],
    queryFn: () => adminGet<ChallengeType[]>('/challenges/types'),
  })

  const STATUS_COLORS: Record<string, string> = {
    phase1: '#6C63FF', phase2: '#FFA502', funded: '#00D4AA',
    failed: '#FF4757', completed: '#4A4A5A',
  }

  return (
    <div className="space-y-4">
      {/* Статус-уведомление */}
      {actionMsg && (
        <div className="rounded-xl px-4 py-3 text-sm font-semibold text-center"
          style={{
            background: actionMsg.startsWith('✅') ? 'rgba(0,212,170,0.15)' : 'rgba(255,71,87,0.15)',
            color: actionMsg.startsWith('✅') ? '#00D4AA' : '#FF4757',
          }}>
          {actionMsg}
        </div>
      )}

      {/* ── 1. Найти пользователя ─── */}
      <div className="glass-card p-4 space-y-3">
        <p className="text-sm font-bold text-white">1. Найти пользователя</p>

        {/* Preset кнопки */}
        <div className="flex gap-2">
          {PRESET_IDS.map(id => (
            <button
              key={id}
              className="flex-1 py-2 rounded-xl text-xs font-bold"
              style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
              onClick={() => { setTgInput(String(id)); findUser(id) }}
              disabled={loading}
            >
              TG {id}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            type="number"
            value={tgInput}
            onChange={e => setTgInput(e.target.value)}
            placeholder="Telegram ID вручную..."
            className="flex-1 bg-bg-border border border-bg-border rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none"
          />
          <button
            className="px-4 py-2.5 rounded-xl text-sm font-bold"
            style={{ background: '#6C63FF', color: '#fff' }}
            onClick={() => tgInput && findUser(Number(tgInput))}
            disabled={loading || !tgInput}
          >
            {loading ? '...' : 'Найти'}
          </button>
        </div>

        {userError && <p className="text-xs text-loss">{userError}</p>}

        {/* Найденный пользователь */}
        {foundUser && (
          <div className="bg-bg-border rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-white">
                  {foundUser.username ? `@${foundUser.username}` : foundUser.first_name}
                </p>
                <p className="text-xs text-text-muted num">
                  ID: {foundUser.telegram_id} · Испытаний: {foundUser.active_challenges}
                </p>
              </div>
              <RoleBadge role={foundUser.role} />
            </div>

            {/* Изменить роль */}
            <p className="text-xs text-text-muted pt-1">Изменить роль:</p>
            <div className="flex flex-wrap gap-1">
              {['challenger', 'funded_trader', 'elite_trader', 'admin', 'super_admin'].map(r => (
                <button
                  key={r}
                  className="px-2 py-1 rounded-lg text-xs font-semibold transition-all"
                  style={{
                    background: foundUser.role === r ? '#6C63FF30' : '#1E1E2E',
                    color: foundUser.role === r ? '#6C63FF' : '#888',
                    border: foundUser.role === r ? '1px solid #6C63FF50' : '1px solid transparent',
                  }}
                  onClick={() => setRole(r)}
                  disabled={loading}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── 2. Выдать испытание ─── */}
      {foundUser && (
        <div className="glass-card p-4 space-y-3">
          <p className="text-sm font-bold text-white">2. Выдать испытание (без оплаты)</p>
          {challengeTypes.length === 0 ? (
            <p className="text-xs text-text-muted">Загрузка типов испытаний...</p>
          ) : (
            <div className="space-y-2">
              {challengeTypes.map(ct => (
                <div key={ct.id} className="flex items-center justify-between bg-bg-border rounded-xl px-3 py-2">
                  <div>
                    <p className="text-sm font-semibold text-white">{ct.name}</p>
                    <p className="text-xs text-text-muted num">${ct.account_size.toLocaleString()} · ${ct.price}</p>
                  </div>
                  <button
                    className="px-3 py-1.5 rounded-lg text-xs font-bold"
                    style={{ background: 'rgba(0,212,170,0.15)', color: '#00D4AA' }}
                    onClick={() => grantChallenge(ct.id, ct.name)}
                    disabled={loading}
                  >
                    + Выдать
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 3. Выбрать испытание ─── */}
      {foundUser && userChallenges.length > 0 && (
        <div className="glass-card p-4 space-y-3">
          <p className="text-sm font-bold text-white">3. Выбрать испытание для управления</p>
          <div className="space-y-2">
            {userChallenges.map(ch => (
              <button
                key={ch.id}
                className="w-full text-left rounded-xl px-3 py-2.5 transition-all"
                style={{
                  background: selectedChallenge?.id === ch.id ? '#6C63FF20' : '#1E1E2E',
                  border: selectedChallenge?.id === ch.id ? '1px solid #6C63FF50' : '1px solid transparent',
                }}
                onClick={() => setSelectedChallenge(ch)}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-white">
                    #{ch.id} {ch.challenge_type_name}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded font-bold"
                    style={{ background: `${STATUS_COLORS[ch.status] ?? '#888'}20`, color: STATUS_COLORS[ch.status] ?? '#888' }}>
                    {ch.status}
                  </span>
                </div>
                <p className="text-xs text-text-muted num mt-0.5">
                  PnL: {ch.total_pnl >= 0 ? '+' : ''}{ch.total_pnl.toFixed(2)} · {ch.trading_days_count} дней
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── 4. Управлять выбранным испытанием ─── */}
      {selectedChallenge && (
        <div className="glass-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-bold text-white">4. Управление #{selectedChallenge.id}</p>
            <span className="text-xs px-2 py-0.5 rounded font-bold"
              style={{ background: `${STATUS_COLORS[selectedChallenge.status] ?? '#888'}20`, color: STATUS_COLORS[selectedChallenge.status] ?? '#888' }}>
              {selectedChallenge.status}
            </span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-bg-border rounded-xl p-2">
              <p className="text-xs text-text-muted">Total PnL</p>
              <p className="num text-sm font-bold" style={{ color: selectedChallenge.total_pnl >= 0 ? '#00D4AA' : '#FF4757' }}>
                {selectedChallenge.total_pnl >= 0 ? '+' : ''}{selectedChallenge.total_pnl.toFixed(2)}
              </p>
            </div>
            <div className="bg-bg-border rounded-xl p-2">
              <p className="text-xs text-text-muted">Дней</p>
              <p className="num text-sm font-bold text-white">{selectedChallenge.trading_days_count}</p>
            </div>
            <div className="bg-bg-border rounded-xl p-2">
              <p className="text-xs text-text-muted">Аккаунт</p>
              <p className="num text-sm font-bold text-white">${selectedChallenge.account_size.toLocaleString()}</p>
            </div>
          </div>

          {/* Force status */}
          <div>
            <p className="text-xs text-text-muted mb-2">Изменить статус:</p>
            <div className="flex flex-wrap gap-2">
              {(['phase1', 'phase2', 'funded', 'failed'] as const).map(s => (
                <button
                  key={s}
                  className="flex-1 min-w-[4rem] py-2 rounded-xl text-xs font-bold transition-all"
                  style={{
                    background: selectedChallenge.status === s ? `${STATUS_COLORS[s]}30` : `${STATUS_COLORS[s]}10`,
                    color: STATUS_COLORS[s],
                    border: selectedChallenge.status === s ? `1px solid ${STATUS_COLORS[s]}60` : '1px solid transparent',
                  }}
                  onClick={() => forceStatus(s)}
                  disabled={loading}
                >
                  {s}
                </button>
              ))}
            </div>
            <button
              className="mt-2 w-full py-2 rounded-xl text-xs font-bold"
              style={{ background: 'rgba(255,71,87,0.1)', color: '#FF4757' }}
              onClick={() => forceStatus(selectedChallenge.status, true)}
              disabled={loading}
            >
              🔄 Сбросить PnL + дни (текущий статус)
            </button>
          </div>

          {/* PnL кнопки */}
          <div>
            <p className="text-xs text-text-muted mb-2">Добавить PnL (+ торговый день):</p>
            <div className="grid grid-cols-4 gap-1.5 mb-2">
              {[100, 500, 1000, 5000].map(v => (
                <button key={v}
                  className="py-2 rounded-xl text-xs font-bold"
                  style={{ background: 'rgba(0,212,170,0.12)', color: '#00D4AA' }}
                  onClick={() => addPnl(v)}
                  disabled={loading}
                >+{v}</button>
              ))}
            </div>
            <div className="grid grid-cols-4 gap-1.5 mb-3">
              {[100, 500, 1000, 5000].map(v => (
                <button key={v}
                  className="py-2 rounded-xl text-xs font-bold"
                  style={{ background: 'rgba(255,71,87,0.12)', color: '#FF4757' }}
                  onClick={() => addPnl(-v)}
                  disabled={loading}
                >-{v}</button>
              ))}
            </div>

            {/* Произвольный PnL */}
            <div className="flex gap-2">
              <input
                type="number"
                value={customPnl}
                onChange={e => setCustomPnl(e.target.value)}
                placeholder="Сумма (может быть отрицательной)"
                className="flex-1 bg-bg-border border border-bg-border rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
              />
              <button
                className="px-4 py-2 rounded-xl text-sm font-bold"
                style={{ background: '#6C63FF', color: '#fff' }}
                onClick={() => { customPnl && addPnl(Number(customPnl)); setCustomPnl('') }}
                disabled={loading || !customPnl}
              >
                Добавить
              </button>
            </div>
          </div>

          {/* Сценарии */}
          <div>
            <p className="text-xs text-text-muted mb-2">Быстрые сценарии:</p>
            <div className="space-y-2">
              <button
                className="w-full py-2.5 rounded-xl text-xs font-bold text-left px-3"
                style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
                onClick={async () => {
                  await forceStatus('phase1', true)
                  for (let i = 0; i < 4; i++) await addPnl(600, true)
                }}
                disabled={loading}
              >
                🔬 Phase 1: сбросить + добавить +2400 за 4 дня
              </button>
              <button
                className="w-full py-2.5 rounded-xl text-xs font-bold text-left px-3"
                style={{ background: 'rgba(255,165,2,0.15)', color: '#FFA502' }}
                onClick={async () => {
                  await forceStatus('phase2', false)
                  for (let i = 0; i < 4; i++) await addPnl(600, true)
                }}
                disabled={loading}
              >
                ⚡ Phase 2: перевести + добавить +2400 за 4 дня
              </button>
              <button
                className="w-full py-2.5 rounded-xl text-xs font-bold text-left px-3"
                style={{ background: 'rgba(0,212,170,0.15)', color: '#00D4AA' }}
                onClick={() => forceStatus('funded')}
                disabled={loading}
              >
                💰 Сразу получить FUNDED + роль funded_trader
              </button>
              <button
                className="w-full py-2.5 rounded-xl text-xs font-bold text-left px-3"
                style={{ background: 'rgba(255,71,87,0.15)', color: '#FF4757' }}
                onClick={() => forceStatus('failed', false)}
                disabled={loading}
              >
                💥 Провалить испытание
              </button>
            </div>
          </div>

          {/* Bybit actions */}
          <div className="border-t border-bg-border pt-3 space-y-2">
            <p className="text-xs text-text-muted">Bybit / системные действия:</p>
            <button
              className="w-full py-2.5 rounded-xl text-xs font-bold text-left px-3"
              style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
              onClick={async () => {
                setLoading(true)
                try {
                  const res = await adminPost<{ bybit_uid: string }>(`/admin/challenges/${selectedChallenge.id}/activate-bybit`, {})
                  msg(`Bybit аккаунт создан: uid=${res.bybit_uid}`)
                  const updated = { ...selectedChallenge, status: 'phase1' }
                  setSelectedChallenge(updated)
                  setUserChallenges(prev => prev.map(c => c.id === updated.id ? updated : c))
                } catch (e: any) { msg(e?.response?.data?.detail ?? 'Ошибка Bybit API', true) }
                finally { setLoading(false) }
              }}
              disabled={loading}
            >
              🔗 Создать Bybit аккаунт и активировать
            </button>
            <button
              className="w-full py-2.5 rounded-xl text-xs font-bold text-left px-3"
              style={{ background: 'rgba(255,71,87,0.08)', color: '#FF4757' }}
              onClick={async () => {
                if (!confirm(`Удалить испытание #${selectedChallenge.id}? Это необратимо.`)) return
                setLoading(true)
                try {
                  await apiClient.delete(`/admin/challenges/${selectedChallenge.id}`)
                  msg(`Испытание #${selectedChallenge.id} удалено`)
                  setSelectedChallenge(null)
                  setUserChallenges(prev => prev.filter(c => c.id !== selectedChallenge.id))
                } catch (e: any) { msg(e?.response?.data?.detail ?? 'Ошибка удаления', true) }
                finally { setLoading(false) }
              }}
              disabled={loading}
            >
              🗑 Удалить испытание #{selectedChallenge.id}
            </button>
          </div>
        </div>
      )}

      {/* ── Инструкция ─── */}
      <div className="glass-card p-4 space-y-2">
        <p className="text-xs font-bold text-white">Инструкция по тестированию:</p>
        <ol className="text-xs text-text-muted space-y-1 list-decimal list-inside">
          <li>Нажми кнопку с TG ID → находит твой аккаунт</li>
          <li>Выдай испытание (без оплаты) через секцию 2</li>
          <li>Выбери испытание в секции 3</li>
          <li>В секции 4 управляй: меняй статус, добавляй PnL</li>
          <li>Используй быстрые сценарии для полного прохождения</li>
          <li>Перейди на /dashboard чтобы увидеть изменения</li>
        </ol>
      </div>
    </div>
  )
}

// ── Overview ──────────────────────────────────────────────────────────────────

function OverviewTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-overview'],
    queryFn: () => adminGet<AdminOverview>('/admin/overview'),
    refetchInterval: 30_000,
  })

  if (isLoading) return <p className="text-text-muted text-center py-8">Загрузка...</p>
  if (!data) return null

  const stats = [
    { label: 'Пользователей', value: data.total_users, icon: '👥', color: '#6C63FF' },
    { label: 'Активных сегодня', value: data.active_users_today, icon: '🟢', color: '#00D4AA' },
    { label: 'Всего испытаний', value: data.total_challenges, icon: '🎯', color: '#FFA502' },
    { label: 'Активных', value: data.active_challenges, icon: '⚡', color: '#FFA502' },
    { label: 'Funded', value: data.funded_accounts, icon: '💎', color: '#00D4AA' },
    { label: 'Выплат ожидает', value: data.pending_payouts, icon: '⏳', color: '#FF4757' },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {stats.map((s) => (
          <motion.div key={s.label} className="glass-card p-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-2 mb-1">
              <span>{s.icon}</span>
              <span className="text-xs text-text-secondary">{s.label}</span>
            </div>
            <p className="num text-2xl font-bold" style={{ color: s.color }}>{s.value.toLocaleString('en')}</p>
          </motion.div>
        ))}
      </div>
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
    queryFn: () => adminGet<{ users: AdminUser[]; total: number }>('/admin/users', {
      limit, offset: page * limit, search: search || undefined,
    }),
    staleTime: 10_000,
  })

  const blockMutation = useMutation({
    mutationFn: ({ userId, block }: { userId: number; block: boolean }) =>
      adminPost(`/admin/users/${userId}/${block ? 'block' : 'unblock'}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  return (
    <div className="space-y-3">
      <input type="text" value={search}
        onChange={e => { setSearch(e.target.value); setPage(0) }}
        placeholder="Поиск по username..."
        className="w-full bg-bg-border border border-bg-border rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none"
      />
      {isLoading ? (
        <p className="text-text-muted text-center py-8">Загрузка...</p>
      ) : (
        <>
          <p className="text-xs text-text-muted">Всего: {data?.total ?? 0}</p>
          <div className="space-y-2">
            {(data?.users ?? []).map(user => (
              <div key={user.id} className="glass-card p-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-white truncate">
                      {user.username ? `@${user.username}` : user.first_name}
                    </p>
                    <RoleBadge role={user.role} />
                    {user.is_blocked && <span className="text-xs text-loss">🚫</span>}
                  </div>
                  <p className="text-xs text-text-muted num">ID: {user.telegram_id} · {user.active_challenges} испытаний</p>
                </div>
                <button
                  className="shrink-0 px-2 py-1 rounded-lg text-xs font-semibold"
                  style={{
                    background: user.is_blocked ? 'rgba(0,212,170,0.1)' : 'rgba(255,71,87,0.1)',
                    color: user.is_blocked ? '#00D4AA' : '#FF4757',
                  }}
                  onClick={() => blockMutation.mutate({ userId: user.id, block: !user.is_blocked })}
                >
                  {user.is_blocked ? 'Разбанить' : 'Бан'}
                </button>
              </div>
            ))}
          </div>
          <Pagination page={page} total={data?.total ?? 0} limit={limit} onPage={setPage} />
        </>
      )}
    </div>
  )
}

// ── Challenges ─────────────────────────────────────────────────────────────────

function ChallengesTab() {
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['admin-challenges', page, statusFilter],
    queryFn: () => adminGet<{ challenges: AdminChallenge[]; total: number }>('/admin/challenges', {
      limit, offset: page * limit,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
    staleTime: 10_000,
  })

  const STATUS_COLORS: Record<string, string> = {
    phase1: '#6C63FF', phase2: '#FFA502', funded: '#00D4AA', failed: '#FF4757', completed: '#00D4AA',
  }
  const STATUS_OPTS = ['all', 'phase1', 'phase2', 'funded', 'failed', 'completed']

  return (
    <div className="space-y-3">
      <div className="flex gap-1 flex-wrap">
        {STATUS_OPTS.map(s => (
          <button key={s}
            className="px-3 py-1 rounded-full text-xs font-semibold transition-all"
            style={{
              background: statusFilter === s ? '#6C63FF20' : '#1E1E2E',
              color: statusFilter === s ? '#6C63FF' : '#4A4A5A',
              border: statusFilter === s ? '1px solid #6C63FF40' : '1px solid transparent',
            }}
            onClick={() => { setStatusFilter(s); setPage(0) }}
          >{s}</button>
        ))}
      </div>
      {isLoading ? (
        <p className="text-text-muted text-center py-8">Загрузка...</p>
      ) : (
        <>
          <p className="text-xs text-text-muted">Всего: {data?.total ?? 0}</p>
          <div className="space-y-2">
            {(data?.challenges ?? []).map(ch => (
              <div key={ch.id} className="glass-card p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">
                      {ch.username ? `@${ch.username}` : `User #${ch.user_id}`}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded font-bold"
                      style={{ background: `${STATUS_COLORS[ch.status] ?? '#888'}20`, color: STATUS_COLORS[ch.status] ?? '#888' }}>
                      {ch.status}
                    </span>
                  </div>
                  <span className="num text-sm font-bold" style={{ color: ch.total_pnl >= 0 ? '#00D4AA' : '#FF4757' }}>
                    {ch.total_pnl >= 0 ? '+' : ''}{ch.total_pnl.toFixed(2)}
                  </span>
                </div>
                <p className="text-xs text-text-muted num">
                  {ch.challenge_type_name} · ${ch.account_size.toLocaleString()} · {ch.trading_days_count}д
                </p>
                {ch.failed_reason && <p className="text-xs text-loss mt-1">⚠️ {ch.failed_reason}</p>}
              </div>
            ))}
          </div>
          <Pagination page={page} total={data?.total ?? 0} limit={limit} onPage={setPage} />
        </>
      )}
    </div>
  )
}

// ── Payouts ───────────────────────────────────────────────────────────────────

function PayoutsTab() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('pending')

  const { data: payouts = [], isLoading } = useQuery({
    queryKey: ['admin-payouts', statusFilter],
    queryFn: () => adminGet<AdminPayout[]>('/admin/payouts', {
      status: statusFilter !== 'all' ? statusFilter : undefined, limit: 50,
    }),
    refetchInterval: 30_000,
  })

  const approveMutation = useMutation({
    mutationFn: (id: number) => adminPost(`/admin/payouts/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-payouts'] }),
  })

  const rejectMutation = useMutation({
    mutationFn: (id: number) => adminPost(`/admin/payouts/${id}/reject`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-payouts'] }),
  })

  return (
    <div className="space-y-3">
      <div className="flex gap-1">
        {['pending', 'approved', 'rejected', 'all'].map(s => (
          <button key={s}
            className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={{ background: statusFilter === s ? '#12121A' : 'transparent', color: statusFilter === s ? '#fff' : '#4A4A5A' }}
            onClick={() => setStatusFilter(s)}
          >{s}</button>
        ))}
      </div>
      {isLoading ? (
        <p className="text-text-muted text-center py-8">Загрузка...</p>
      ) : payouts.length === 0 ? (
        <p className="text-center text-text-muted py-8">Нет выплат</p>
      ) : (
        <div className="space-y-2">
          {payouts.map(p => (
            <div key={p.id} className="glass-card p-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-semibold text-white">
                    {p.username ? `@${p.username}` : `User #${p.user_id}`}
                  </p>
                  <p className="num text-xs text-text-muted">{p.network} · Challenge #{p.challenge_id}</p>
                </div>
                <p className="num text-lg font-bold text-profit">${p.amount.toFixed(2)}</p>
              </div>
              <p className="num text-xs text-text-muted mb-2 break-all">{p.wallet_address}</p>
              {p.status === 'pending' && (
                <div className="flex gap-2">
                  <button className="flex-1 py-1.5 rounded-lg text-xs font-bold"
                    style={{ background: 'rgba(0,212,170,0.15)', color: '#00D4AA' }}
                    onClick={() => approveMutation.mutate(p.id)} disabled={approveMutation.isPending}>
                    ✓ Одобрить
                  </button>
                  <button className="flex-1 py-1.5 rounded-lg text-xs font-bold"
                    style={{ background: 'rgba(255,71,87,0.15)', color: '#FF4757' }}
                    onClick={() => rejectMutation.mutate(p.id)} disabled={rejectMutation.isPending}>
                    ✗ Отклонить
                  </button>
                </div>
              )}
              {p.status !== 'pending' && (
                <p className="text-xs font-semibold"
                  style={{ color: p.status === 'approved' ? '#00D4AA' : '#FF4757' }}>
                  {p.status === 'approved' ? '✓ Одобрено' : '✗ Отклонено'}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Shared ────────────────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  const config: Record<string, { label: string; color: string }> = {
    super_admin:   { label: 'SUPER',   color: '#FF4757' },
    admin:         { label: 'ADMIN',   color: '#FFA502' },
    funded_trader: { label: 'FUNDED',  color: '#00D4AA' },
    elite_trader:  { label: 'ELITE',   color: '#FFD700' },
    challenger:    { label: 'TRADER',  color: '#6C63FF' },
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
      <button className="px-4 py-2 rounded-xl text-sm text-text-secondary disabled:opacity-30"
        style={{ background: '#1E1E2E' }} onClick={() => onPage(page - 1)} disabled={page === 0}>
        ← Назад
      </button>
      <span className="text-xs text-text-muted">{page + 1} / {maxPage + 1}</span>
      <button className="px-4 py-2 rounded-xl text-sm text-text-secondary disabled:opacity-30"
        style={{ background: '#1E1E2E' }} onClick={() => onPage(page + 1)} disabled={page >= maxPage}>
        Вперёд →
      </button>
    </div>
  )
}
