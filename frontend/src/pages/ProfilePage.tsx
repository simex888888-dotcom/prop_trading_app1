/**
 * ProfilePage — профиль трейдера: ранг, достижения, лидерборд, реферальная программа.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { achievementsApi, leaderboardApi, referralApi, statsApi } from '@/api/client'
import { useAppStore } from '@/store/appStore'
import { useAuthStore } from '@/store/authStore'
import { AchievementBadge } from '@/components/animated/AchievementBadge'
import { AnimatedRank, getRankByStats } from '@/components/animated/AnimatedRank'
import { CardSkeleton } from '@/components/ui/LoadingSkeleton'
import { BottomSheet } from '@/components/ui/BottomSheet'

type ProfileTab = 'achievements' | 'leaderboard' | 'referral'

export function ProfilePage() {
  const activeChallengeId = useAppStore((s) => s.activeChallengeId)
  const [activeTab, setActiveTab] = useState<ProfileTab>('achievements')
  const [shareSheet, setShareSheet] = useState(false)

  const { data: performance } = useQuery({
    queryKey: ['performance', activeChallengeId],
    queryFn: () => statsApi.getPerformance(activeChallengeId!),
    enabled: !!activeChallengeId,
  })

  const { data: achievements = [], isLoading: achLoading } = useQuery({
    queryKey: ['achievements-unlocked'],
    queryFn: () => achievementsApi.getUnlocked(),
  })

  const { data: allAchievements = [] } = useQuery({
    queryKey: ['achievements-all'],
    queryFn: () => achievementsApi.getAll(),
  })

  const { data: leaderboard = [], isLoading: lbLoading } = useQuery({
    queryKey: ['leaderboard-monthly'],
    queryFn: () => leaderboardApi.getMonthly(),
    staleTime: 60_000,
  })

  const { data: referral, isLoading: refLoading } = useQuery({
    queryKey: ['referral-info'],
    queryFn: () => referralApi.getInfo(),
  })

  const rank = performance
    ? getRankByStats(performance.total_trades ?? 0, performance.win_rate ?? 0)
    : null

  const unlockedIds = new Set(achievements.map((a) => a.id))

  return (
    <div className="flex flex-col pb-24 bg-bg-primary min-h-dvh">
      {/* Rank card */}
      <div className="mx-4 mt-4 glass-card p-5 flex items-center gap-4">
        <AnimatedRank
          rank={rank ?? 'isotope'}
          size={80}
        />
        <div className="flex-1 min-w-0">
          <p className="text-text-secondary text-xs mb-1">Твой ранг</p>
          <p className="font-bold text-white text-lg">{rank ? rank.charAt(0).toUpperCase() + rank.slice(1) : 'Isotope'}</p>
          <div className="flex gap-3 mt-2">
            <div>
              <p className="text-xs text-text-muted">Сделок</p>
              <p className="num text-sm font-semibold text-white">{performance?.total_trades ?? 0}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Win Rate</p>
              <p className="num text-sm font-semibold" style={{ color: '#00D4AA' }}>
                {(performance?.win_rate ?? 0).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Достижений</p>
              <p className="num text-sm font-semibold text-white">{achievements.length}</p>
            </div>
          </div>
        </div>
        <button
          onClick={() => setShareSheet(true)}
          className="shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold"
          style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
        >
          Поделиться
        </button>
      </div>

      {/* Tabs */}
      <div className="mx-4 mt-4 flex gap-1 p-1 bg-bg-border rounded-xl">
        {(['achievements', 'leaderboard', 'referral'] as ProfileTab[]).map((tab) => (
          <button
            key={tab}
            className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: activeTab === tab ? '#12121A' : 'transparent',
              color: activeTab === tab ? '#fff' : '#4A4A5A',
            }}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'achievements' ? '🏆 Достижения'
              : tab === 'leaderboard' ? '📊 Рейтинг'
              : '👥 Рефералы'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="px-4 mt-4">
        {activeTab === 'achievements' && (
          <AchievementsTab
            allAchievements={allAchievements}
            unlockedIds={unlockedIds}
            isLoading={achLoading}
          />
        )}
        {activeTab === 'leaderboard' && (
          <LeaderboardTab entries={leaderboard} isLoading={lbLoading} />
        )}
        {activeTab === 'referral' && (
          <ReferralTab referral={referral} isLoading={refLoading} />
        )}
      </div>

      {/* Share sheet */}
      <BottomSheet isOpen={shareSheet} onClose={() => setShareSheet(false)} title="Поделиться профилем" height="50vh">
        <div className="px-5 py-4 space-y-4">
          <div
            className="rounded-2xl p-5 text-center"
            style={{
              background: 'linear-gradient(135deg, #12121A, #1E1E2E)',
              border: '1px solid #6C63FF30',
            }}
          >
            <p className="text-text-muted text-xs mb-2 tracking-widest uppercase">CHM KRYPTON Trader</p>
            <p className="text-2xl font-bold text-white mb-1">{rank ? rank.charAt(0).toUpperCase() + rank.slice(1) : 'Isotope'}</p>
            <p className="num text-profit text-lg">{(performance?.win_rate ?? 0).toFixed(1)}% Win Rate</p>
            <p className="num text-text-secondary text-sm mt-1">{performance?.total_trades ?? 0} сделок</p>
            <p className="text-text-muted text-xs mt-3">t.me/chm_krypton</p>
          </div>
          <p className="text-center text-text-muted text-xs">Нажми на карточку чтобы сохранить</p>
        </div>
      </BottomSheet>
    </div>
  )
}

function AchievementsTab({
  allAchievements,
  unlockedIds,
  isLoading,
}: {
  allAchievements: any[]
  unlockedIds: Set<string>
  isLoading: boolean
}) {
  if (isLoading) return <CardSkeleton />

  const unlocked = allAchievements.filter((a) => unlockedIds.has(a.id))
  const locked = allAchievements.filter((a) => !unlockedIds.has(a.id))

  return (
    <div className="space-y-4">
      {unlocked.length > 0 && (
        <div>
          <p className="text-xs text-text-secondary mb-2 uppercase tracking-wider">
            Получены ({unlocked.length})
          </p>
          <div className="grid grid-cols-3 gap-3">
            {unlocked.map((ach) => (
              <motion.div
                key={ach.id}
                className="flex flex-col items-center gap-1.5"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
              >
                <AchievementBadge
                  name={ach.name}
                  lottieSrc={ach.lottie_file}
                  level={ach.level || 'gold'}
                  progress={ach.progress}
                />
                <p className="text-xs text-white text-center leading-tight">{ach.name}</p>
              </motion.div>
            ))}
          </div>
        </div>
      )}
      {locked.length > 0 && (
        <div>
          <p className="text-xs text-text-secondary mb-2 uppercase tracking-wider">
            Заблокированы ({locked.length})
          </p>
          <div className="grid grid-cols-3 gap-3">
            {locked.map((ach) => (
              <div key={ach.id} className="flex flex-col items-center gap-1.5">
                <AchievementBadge
                  name={ach.name}
                  lottieSrc={ach.lottie_file}
                  level="locked"
                  progress={ach.progress}
                />
                <p className="text-xs text-text-muted text-center leading-tight">{ach.name}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {allAchievements.length === 0 && (
        <p className="text-center text-text-muted py-8">Нет доступных достижений</p>
      )}
    </div>
  )
}

function LeaderboardTab({ entries, isLoading }: { entries: any[]; isLoading: boolean }) {
  if (isLoading) return <CardSkeleton />

  return (
    <div className="space-y-2">
      {entries.length === 0 ? (
        <p className="text-center text-text-muted py-8">Рейтинг пуст</p>
      ) : (
        entries.map((entry, i) => (
          <div
            key={entry.user_id ?? i}
            className="glass-card p-3 flex items-center gap-3"
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0"
              style={{
                background: i === 0 ? 'linear-gradient(135deg,#FFD700,#FFA500)'
                  : i === 1 ? 'linear-gradient(135deg,#C0C0C0,#A0A0A0)'
                  : i === 2 ? 'linear-gradient(135deg,#CD7F32,#A0522D)'
                  : '#1E1E2E',
                color: i < 3 ? '#fff' : '#4A4A5A',
              }}
            >
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">
                {entry.username ?? `User #${i + 1}`}
              </p>
              <p className="text-xs text-text-muted">{entry.rank_name ?? 'Isotope'}</p>
            </div>
            <div className="text-right">
              <p className="num text-sm font-bold" style={{ color: '#00D4AA' }}>
                +{(entry.total_pnl ?? 0).toFixed(0)} USDT
              </p>
              <p className="num text-xs text-text-muted">{(entry.win_rate ?? 0).toFixed(1)}% WR</p>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function ReferralTab({ referral, isLoading }: { referral: any; isLoading: boolean }) {
  const copyLink = () => {
    if (referral?.referral_link) {
      navigator.clipboard.writeText(referral.referral_link).catch(() => {})
    }
  }

  if (isLoading) return <CardSkeleton />

  return (
    <div className="space-y-4">
      {/* Referral link */}
      <div className="glass-card p-4">
        <p className="text-text-secondary text-xs mb-2">Твоя реферальная ссылка</p>
        <div className="flex items-center gap-2">
          <p className="num text-xs text-white flex-1 truncate">
            {referral?.referral_link ?? 'Загрузка...'}
          </p>
          <button
            onClick={copyLink}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0"
            style={{ background: 'rgba(108,99,255,0.15)', color: '#6C63FF' }}
          >
            Копировать
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="glass-card p-4 text-center">
          <p className="text-2xl font-bold text-white num">{referral?.total_referrals ?? 0}</p>
          <p className="text-xs text-text-secondary mt-1">Приглашённых</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-2xl font-bold num" style={{ color: '#00D4AA' }}>
            {(referral?.total_earned ?? 0).toFixed(0)} USDT
          </p>
          <p className="text-xs text-text-secondary mt-1">Заработано</p>
        </div>
      </div>

      {/* Tiers info */}
      <div className="glass-card p-4 space-y-3">
        <p className="text-sm font-semibold text-white mb-3">Комиссии</p>
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-profit" />
            <span className="text-sm text-text-secondary">Уровень 1 (прямые)</span>
          </div>
          <span className="num text-sm font-bold text-white">10%</span>
        </div>
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ background: '#6C63FF' }} />
            <span className="text-sm text-text-secondary">Уровень 2 (через рефералов)</span>
          </div>
          <span className="num text-sm font-bold text-white">3%</span>
        </div>
        <p className="text-xs text-text-muted pt-2 border-t border-bg-border">
          Выплаты происходят еженедельно по понедельникам
        </p>
      </div>
    </div>
  )
}
