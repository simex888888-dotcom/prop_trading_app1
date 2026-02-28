/**
 * Axios HTTP клиент для CHM_KRYPTON API.
 */
import axios, { AxiosError, AxiosResponse } from 'axios'
import { useAuthStore } from '@/store/authStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request Interceptor: добавляем JWT ──────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response Interceptor: обновление токена при 401 ────────────────────────
let refreshing = false

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config
    if (
      error.response?.status === 401 &&
      !refreshing &&
      original
    ) {
      refreshing = true
      try {
        const store = useAuthStore.getState()
        const refreshToken = store.refreshToken
        if (refreshToken) {
          const resp = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          const { access_token, refresh_token } = resp.data.data
          store.setTokens(access_token, refresh_token)
          original.headers!.Authorization = `Bearer ${access_token}`
          return apiClient(original)
        }
      } catch {
        useAuthStore.getState().logout()
      } finally {
        refreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// ── API Methods ─────────────────────────────────────────────────────────────

export type APIResponse<T> = {
  success: boolean
  data: T
  message?: string
}

async function get<T>(url: string, params?: object): Promise<T> {
  const resp = await apiClient.get<APIResponse<T>>(url, { params })
  return resp.data.data
}

async function post<T>(url: string, body?: object): Promise<T> {
  const resp = await apiClient.post<APIResponse<T>>(url, body)
  return resp.data.data
}

async function del<T>(url: string, params?: object): Promise<T> {
  const resp = await apiClient.delete<APIResponse<T>>(url, { params })
  return resp.data.data
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  loginTelegram: (initData: string, referralCode?: string) =>
    post<{
      access_token: string
      refresh_token: string
      user_id: number
      role: string
      is_new: boolean
    }>('/auth/telegram', { init_data: initData, referral_code: referralCode }),
}

// ── Challenges ────────────────────────────────────────────────────────────────
export const challengesApi = {
  list: () => get<ChallengeType[]>('/challenges'),
  my: (status?: string) => get<UserChallenge[]>('/challenges/my', { status }),
  getById: (id: number) => get<UserChallenge>(`/challenges/${id}`),
  getDetail: (id: number) => get<UserChallenge>(`/challenges/${id}`),
  getRules: (id: number) => get<ChallengeRules>(`/challenges/${id}/rules`),
  getViolations: (id: number) => get<Violation[]>(`/challenges/${id}/violations`),
  purchase: (challengeTypeId: number) =>
    post<UserChallenge>('/challenges/purchase', { challenge_type_id: challengeTypeId }),
}

// ── Trading ──────────────────────────────────────────────────────────────────
export const tradingApi = {
  getBalance: (challengeId: number) =>
    get<Balance>('/trading/balance', { challenge_id: challengeId }),
  getPositions: (challengeId: number) =>
    get<Position[]>('/trading/positions', { challenge_id: challengeId }),
  getOrders: (challengeId: number) =>
    get<Order[]>('/trading/orders', { challenge_id: challengeId }),
  placeOrder: (order: PlaceOrderRequest) => post<object>('/trading/order', order),
  cancelOrder: (orderId: string, challengeId: number, symbol: string) =>
    del<object>(`/trading/order/${orderId}`, { challenge_id: challengeId, symbol }),
  closeAllPositions: (challengeId: number) =>
    del<object[]>('/trading/positions/all', { challenge_id: challengeId }),
  getHistory: (challengeId: number, params?: { cursor?: number; limit?: number; side?: string; symbol?: string }) =>
    get<TradeHistoryPage>('/trading/history', {
      challenge_id: challengeId,
      cursor: params?.cursor,
      limit: params?.limit ?? 50,
      side: params?.side,
      symbol: params?.symbol,
    }),
  getPairs: () => get<TradingPair[]>('/trading/pairs'),
  getKline: (symbol: string, interval: string, limit = 200) =>
    get<KlineBar[]>('/trading/kline', { symbol, interval, limit }),
}

// ── Stats ─────────────────────────────────────────────────────────────────────
export const statsApi = {
  getDashboard: (challengeId?: number) =>
    get<Dashboard>('/stats/dashboard', challengeId ? { challenge_id: challengeId } : undefined),
  getEquityCurve: (challengeId: number) =>
    get<EquityPoint[]>('/stats/equity-curve', { challenge_id: challengeId }),
  getPerformance: (challengeId: number) =>
    get<Performance>('/stats/performance', { challenge_id: challengeId }),
}

// ── Payouts ──────────────────────────────────────────────────────────────────
export const payoutsApi = {
  list: (challengeId?: number) => get<Payout[]>('/payouts', challengeId ? { challenge_id: challengeId } : undefined),
  getList: (challengeId: number) => get<Payout[]>('/payouts', { challenge_id: challengeId }),
  getAvailable: (challengeId: number) =>
    get<AvailablePayout>('/payouts/available', { challenge_id: challengeId }),
  request: (data: PayoutRequest) => post<Payout>('/payouts/request', data),
}

// ── Achievements ──────────────────────────────────────────────────────────────
export const achievementsApi = {
  all: () => get<Achievement[]>('/achievements'),
  getAll: () => get<Achievement[]>('/achievements'),
  unlocked: () => get<Achievement[]>('/achievements/unlocked'),
  getUnlocked: () => get<Achievement[]>('/achievements/unlocked'),
}

// ── Leaderboard ───────────────────────────────────────────────────────────────
export const leaderboardApi = {
  monthly: (limit = 100) => get<LeaderboardEntry[]>('/leaderboard/monthly', { limit }),
  getMonthly: (limit = 100) => get<LeaderboardEntry[]>('/leaderboard/monthly', { limit }),
  alltime: (limit = 100) => get<LeaderboardEntry[]>('/leaderboard/alltime', { limit }),
  getAlltime: (limit = 100) => get<LeaderboardEntry[]>('/leaderboard/alltime', { limit }),
}

// ── Referral ──────────────────────────────────────────────────────────────────
export const referralApi = {
  info: () => get<ReferralInfo>('/referral/info'),
  getInfo: () => get<ReferralInfo>('/referral/info'),
  earnings: () => get<ReferralEarning[]>('/referral/earnings'),
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface ChallengeType {
  id: number
  name: string
  description?: string
  rank_icon?: string
  gradient_bg?: string
  account_size: number
  price: number
  profit_target_p1: number
  profit_target_p2: number
  max_daily_loss: number
  max_total_loss: number
  min_trading_days: number
  drawdown_type: string
  is_one_phase: boolean
  is_instant: boolean
  is_refundable: boolean
  max_leverage: number
  profit_split_pct: number
}

export interface UserChallenge {
  id: number
  challenge_type_id: number
  challenge_type?: ChallengeType
  status: 'phase1' | 'phase2' | 'funded' | 'failed' | 'completed'
  phase: number | null
  account_mode: 'demo' | 'funded'
  initial_balance: number
  current_balance: number
  daily_pnl: number
  total_pnl: number
  trading_days_count: number
  scaling_step?: number
  started_at?: string
  funded_at?: string
  failed_at?: string
  failed_reason?: string
}

export interface ChallengeRules {
  challenge_id: number
  challenge_type_name?: string
  phase?: string
  status: string
  profit_target_pct: number
  profit_target_amount: number
  daily_loss_limit_pct?: number
  daily_loss_used_pct?: number
  total_loss_limit_pct?: number
  total_loss_used_pct?: number
  max_daily_loss_pct: number
  max_total_loss_pct: number
  min_trading_days: number
  drawdown_type: string
  current_pnl: number
  current_pnl_pct: number
  current_profit_pct?: number
  daily_pnl: number
  trading_days_count: number
  max_loss_today: number
  profit_progress_pct: number
  daily_drawdown_used_pct: number
  total_drawdown_used_pct: number
  initial_balance?: number
  news_trading_ban?: boolean
  overnight_positions_allowed?: boolean
  weekend_positions_allowed?: boolean
  consistency_rule?: boolean
  days_remaining?: number
}

export interface Violation {
  id: number
  type: string
  description: string
  value: number
  limit_value: number
  occurred_at: string
}

export interface Balance {
  wallet_balance: number
  unrealized_pnl: number
  equity: number
  available_balance: number
  account_mode: string
  challenge_id: number
}

export interface Position {
  symbol: string
  side: string
  size: number
  avg_price: number
  unrealized_pnl: number
  leverage: number
  take_profit?: number
  stop_loss?: number
}

export interface Order {
  order_id: string
  symbol: string
  side: string
  order_type: string
  qty: number
  price?: number
  status: string
  created_time: string
}

export interface PlaceOrderRequest {
  symbol: string
  side: 'Buy' | 'Sell'
  order_type: 'Market' | 'Limit'
  qty: string
  price?: string
  stop_loss?: string
  take_profit?: string
  reduce_only?: boolean
  challenge_id: number
}

export interface TradeHistory {
  trade_id?: string
  id?: number
  symbol: string
  side: string
  direction?: string
  qty: number
  quantity?: number
  entry_price?: number
  exit_price?: number
  pnl: number
  pnl_pct?: number
  created_at: string
  closed_at?: string
  opened_at?: string
  leverage?: number
  duration_seconds?: number
}

export interface TradeHistoryPage {
  trades: TradeHistory[]
  next_cursor?: number
  has_more: boolean
}

export interface TradingPair {
  symbol: string
  price: number
  change_24h_pct: number
  volume_24h: number
  high_24h: number
  low_24h: number
}

export interface KlineBar {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface Dashboard {
  active_challenge_id?: number
  challenge_status?: string
  account_mode?: string
  phase?: number
  current_balance: number
  initial_balance: number
  equity: number
  daily_pnl: number
  total_pnl: number
  total_pnl_pct: number
  profit_target_pct: number
  profit_progress_pct: number
  daily_dd_pct: number
  total_dd_pct: number
  daily_dd_limit: number
  total_dd_limit: number
  trading_days_count: number
  min_trading_days: number
  streak_days: number
}

export interface EquityPoint {
  timestamp: number
  equity: number
  pnl: number
}

export interface Performance {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_profit: number
  avg_loss: number
  profit_factor: number
  avg_rr: number
  max_drawdown_pct: number
  best_trade_pnl: number
  worst_trade_pnl: number
  avg_duration_hours: number
}

export interface Payout {
  payout_id?: string
  id?: number
  challenge_id: number
  amount: number
  fee?: number
  net_amount?: number
  wallet_address: string
  network: string
  status: string
  created_at: string
  requested_at?: string
  processed_at?: string
  tx_hash?: string
}

export interface PayoutRequest {
  challenge_id: number
  amount: number
  wallet_address: string
  network: string
}

export interface AvailablePayout {
  challenge_id: number
  available_amount: number
  profit_split_pct: number
  min_payout: number
  can_request: boolean
  pending_payout: boolean
  total_paid?: number
}

export interface Achievement {
  id: number
  key: string
  name: string
  description: string
  lottie_file?: string
  levels_config: Record<string, number>
  level: string
  progress: number
  unlocked_at?: string
}

export interface LeaderboardEntry {
  rank: number
  user_id: number
  username?: string
  first_name: string
  avatar_url?: string
  total_pnl_pct: number
  total_pnl: number
  account_size: number
  trading_days: number
}

export interface ReferralInfo {
  referral_code: string
  referral_link: string
  total_referrals: number
  level1_count: number
  level2_count: number
  total_earned: number
  pending_payout: number
}

export interface ReferralEarning {
  id: number
  referred_username?: string
  bonus_amount: number
  level: number
  paid: boolean
  paid_at?: string
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  next_cursor?: string
  has_more: boolean
  total?: number
}
