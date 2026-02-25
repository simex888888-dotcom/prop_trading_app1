import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getAccountOverview, getPrices, getOpenTrades, closeTrade, checkTpSl } from "../api/index.js";
import { PnLCard } from "../components/PnLCard.jsx";
import { ProgressBar } from "../components/ProgressBar.jsx";
import { FailedOverlay } from "../components/FailedOverlay.jsx";

const PHASE_LABELS = {
  EVALUATION: "Фаза 1 · Evaluation",
  VERIFICATION: "Фаза 2 · Verification",
  FUNDED: "Funded Trader 💰",
};

export default function Dashboard({ hapticFeedback }) {
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [openTrades, setOpenTrades] = useState([]);
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [closingId, setClosingId] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [overview, trades, pricesData] = await Promise.all([
        getAccountOverview(),
        getOpenTrades(),
        getPrices(),
      ]);
      setAccount(overview);
      setOpenTrades(trades);
      setPrices(pricesData.prices || {});
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Обновляем данные каждые 15 секунд
    const interval = setInterval(async () => {
      try {
        const [overview, trades, pricesData] = await Promise.all([
          getAccountOverview(),
          getOpenTrades(),
          getPrices(),
        ]);
        setAccount(overview);
        setOpenTrades(trades);
        setPrices(pricesData.prices || {});
        // Проверяем TP/SL
        await checkTpSl();
      } catch {}
    }, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  async function handleCloseTrade(tradeId) {
    hapticFeedback && hapticFeedback("impact", "medium");
    setClosingId(tradeId);
    try {
      await closeTrade(tradeId);
      hapticFeedback && hapticFeedback("notification", "success");
      await loadData();
    } catch (e) {
      hapticFeedback && hapticFeedback("notification", "error");
    } finally {
      setClosingId(null);
    }
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <span style={{ color: "var(--text-secondary)", fontSize: 14 }}>Загрузка...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="loading-screen">
        <div style={{ fontSize: 40 }}>⚠️</div>
        <p style={{ color: "var(--accent-red)", textAlign: "center" }}>{error}</p>
        <button className="btn btn-primary" style={{ maxWidth: 200 }} onClick={loadData}>
          Повторить
        </button>
      </div>
    );
  }

  if (!account) return null;

  const dailyPnl = parseFloat(account.daily_pnl || 0);
  const unrealizedPnl = parseFloat(account.unrealized_pnl || 0);
  const equity = parseFloat(account.equity || 0);
  const balance = parseFloat(account.current_balance || 0);
  const profitProgress = parseFloat(account.profit_progress_pct || 0);
  const dailyDd = parseFloat(account.daily_drawdown_pct || 0);
  const trailingDd = parseFloat(account.trailing_drawdown_pct || 0);
  const maxDailyDd = parseFloat(account.max_daily_drawdown_pct || 5);
  const maxTrailingDd = parseFloat(account.max_trailing_drawdown_pct || 10);

  return (
    <>
      <FailedOverlay
        account={account}
        onRestarted={(newAccount) => {
          setAccount({ ...account, ...newAccount, status: "ACTIVE" });
        }}
      />

      <div className="page">
        {/* Header */}
        <div
          style={{
            padding: "16px 16px 12px",
            background: "var(--bg-secondary)",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <div className="row" style={{ marginBottom: 8 }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 4 }}>
                {PHASE_LABELS[account.phase] || account.phase}
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.5px" }}>
                ${parseFloat(account.current_balance).toLocaleString("en", { minimumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                Equity: ${equity.toLocaleString("en", { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
              <span className={`phase-badge phase-${account.phase}`}>{account.phase}</span>
              <span
                style={{
                  fontSize: 11,
                  color: "var(--text-muted)",
                  background: "var(--bg-card)",
                  padding: "2px 8px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                }}
              >
                Попытка #{account.attempt_number}
              </span>
            </div>
          </div>

          {/* Progress to target */}
          <ProgressBar
            value={profitProgress}
            max={100}
            label={`Прогресс к цели +${account.profit_target_pct}%`}
            sublabel={`${profitProgress.toFixed(1)}%`}
          />
        </div>

        <div className="page-content">
          {/* Daily PnL */}
          <PnLCard
            pnl={account.daily_pnl}
            pnlPct={account.daily_drawdown_pct}
            label="Дневной PnL"
          />

          {/* Unrealized PnL (если есть открытые позиции) */}
          {openTrades.length > 0 && (
            <PnLCard
              pnl={account.unrealized_pnl}
              label={`Нереализованный PnL (${openTrades.length} позиц.)`}
              size="medium"
            />
          )}

          {/* Risk meters */}
          <div className="card">
            <h3 style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Контроль риска
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <ProgressBar
                value={Math.abs(Math.min(dailyDd, 0))}
                max={maxDailyDd}
                label="Дневная просадка"
                sublabel={`${dailyDd.toFixed(2)}% / -${maxDailyDd}%`}
                color={Math.abs(dailyDd) > maxDailyDd * 0.7 ? "red" : "green"}
              />
              <ProgressBar
                value={Math.max(trailingDd, 0)}
                max={maxTrailingDd}
                label="Trailing просадка"
                sublabel={`${trailingDd.toFixed(2)}% / ${maxTrailingDd}%`}
                color={trailingDd > maxTrailingDd * 0.7 ? "red" : "green"}
              />
            </div>
          </div>

          {/* Stats */}
          <div className="card">
            <h3 style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Статистика
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {[
                { label: "Торговых дней", value: `${account.trading_days_count}/${account.min_trading_days}` },
                { label: "Win Rate", value: `${parseFloat(account.win_rate || 0).toFixed(1)}%` },
                { label: "Сделок", value: account.total_trades },
                { label: "Пиковый Equity", value: `$${parseFloat(account.peak_equity).toLocaleString("en", { minimumFractionDigits: 0 })}` },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    background: "var(--bg-secondary)",
                    borderRadius: 10,
                    padding: "10px 12px",
                  }}
                >
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 4 }}>{item.label}</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Open positions */}
          {openTrades.length > 0 && (
            <div>
              <h3
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  marginBottom: 8,
                  color: "var(--text-secondary)",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Открытые позиции ({openTrades.length})
              </h3>
              {openTrades.map((trade) => {
                const currentPrice = prices[trade.symbol] ? parseFloat(prices[trade.symbol]) : null;
                const upnl = trade.unrealized_pnl ? parseFloat(trade.unrealized_pnl) : null;
                const isLong = trade.direction === "LONG";

                return (
                  <motion.div
                    key={trade.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card"
                    style={{ marginBottom: 8 }}
                  >
                    <div className="row" style={{ marginBottom: 8 }}>
                      <div style={{ display: "flex", align: "center", gap: 8 }}>
                        <span style={{ fontWeight: 700, fontSize: 15 }}>
                          {trade.symbol.replace("USDT", "/USDT")}
                        </span>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: 6,
                            background: isLong ? "var(--accent-green-dim)" : "var(--accent-red-dim)",
                            color: isLong ? "var(--accent-green)" : "var(--accent-red)",
                          }}
                        >
                          {trade.direction} {trade.leverage}x
                        </span>
                      </div>
                      {upnl !== null && (
                        <span
                          style={{
                            fontWeight: 700,
                            fontSize: 15,
                            color: upnl >= 0 ? "var(--accent-green)" : "var(--accent-red)",
                          }}
                        >
                          {upnl >= 0 ? "+" : ""}${upnl.toFixed(2)}
                        </span>
                      )}
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6, marginBottom: 10 }}>
                      {[
                        { label: "Вход", value: `$${parseFloat(trade.entry_price).toLocaleString("en")}` },
                        {
                          label: "TP",
                          value: `$${parseFloat(trade.take_profit).toLocaleString("en")}`,
                          color: "var(--accent-green)",
                        },
                        {
                          label: "SL",
                          value: `$${parseFloat(trade.stop_loss).toLocaleString("en")}`,
                          color: "var(--accent-red)",
                        },
                      ].map((item) => (
                        <div key={item.label} style={{ textAlign: "center" }}>
                          <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 2 }}>{item.label}</div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: item.color || "var(--text-primary)" }}>
                            {item.value}
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: 13 }}
                      onClick={() => handleCloseTrade(trade.id)}
                      disabled={closingId === trade.id}
                    >
                      {closingId === trade.id ? (
                        <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                      ) : (
                        "Закрыть позицию"
                      )}
                    </button>
                  </motion.div>
                );
              })}
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 10 }}>
            <button
              className="btn btn-primary"
              style={{ flex: 2 }}
              onClick={() => {
                hapticFeedback && hapticFeedback("selection");
                navigate("/trade");
              }}
              disabled={account.status === "FAILED"}
            >
              📈 Открыть сделку
            </button>
            <button
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={() => navigate("/history")}
            >
              История
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
