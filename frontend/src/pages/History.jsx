import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getTradeHistory } from "../api/index.js";

const CLOSE_REASON_LABELS = {
  MANUAL: "Вручную",
  TAKE_PROFIT: "🎯 Take Profit",
  STOP_LOSS: "🛑 Stop Loss",
  DAILY_DRAWDOWN: "⚠️ Дневной лимит",
  TRAILING_DRAWDOWN: "⚠️ Trailing",
};

export default function History() {
  const navigate = useNavigate();
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState(null);

  const LIMIT = 20;

  const loadTrades = useCallback(async (offset = 0) => {
    try {
      const data = await getTradeHistory(LIMIT, offset);
      if (offset === 0) {
        setTrades(data);
      } else {
        setTrades((prev) => [...prev, ...data]);
      }
      setHasMore(data.length === LIMIT);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    loadTrades(0);
  }, [loadTrades]);

  function loadMore() {
    setLoadingMore(true);
    loadTrades(trades.length);
  }

  // Статистика
  const totalPnl = trades.reduce((sum, t) => sum + parseFloat(t.realized_pnl || 0), 0);
  const winners = trades.filter((t) => parseFloat(t.realized_pnl || 0) > 0);
  const winRate = trades.length > 0 ? (winners.length / trades.length * 100).toFixed(1) : "0";

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <button
          onClick={() => navigate(-1)}
          style={{
            background: "none",
            color: "var(--accent-green)",
            fontSize: 15,
            fontWeight: 600,
            minWidth: 44,
            minHeight: 44,
            display: "flex",
            alignItems: "center",
          }}
        >
          ←
        </button>
        <h1>История сделок</h1>
      </div>

      <div className="page-content">
        {/* Summary */}
        {trades.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 8,
            }}
          >
            {[
              {
                label: "Итого PnL",
                value: `${totalPnl >= 0 ? "+" : ""}$${Math.abs(totalPnl).toFixed(2)}`,
                color: totalPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)",
              },
              { label: "Сделок", value: trades.length, color: "var(--text-primary)" },
              { label: "Win Rate", value: `${winRate}%`, color: "var(--text-primary)" },
            ].map((item) => (
              <div
                key={item.label}
                className="card"
                style={{ textAlign: "center", padding: "10px 8px" }}
              >
                <div style={{ fontSize: 10, color: "var(--text-secondary)", marginBottom: 4 }}>
                  {item.label}
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: item.color }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div style={{ color: "var(--accent-red)", textAlign: "center", padding: 20 }}>{error}</div>
        )}

        {!error && trades.length === 0 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "40px 20px",
              gap: 12,
            }}
          >
            <div style={{ fontSize: 48 }}>📭</div>
            <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
              История пустая. Откройте первую сделку!
            </p>
            <button className="btn btn-primary" style={{ maxWidth: 200 }} onClick={() => navigate("/trade")}>
              Открыть сделку
            </button>
          </div>
        )}

        {trades.map((trade, i) => {
          const pnl = parseFloat(trade.realized_pnl || 0);
          const isPositive = pnl >= 0;
          const isLong = trade.direction === "LONG";
          const closeDate = trade.closed_at ? new Date(trade.closed_at) : null;

          return (
            <motion.div
              key={trade.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="card"
            >
              <div className="row" style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", align: "center", gap: 8 }}>
                  <span style={{ fontWeight: 700 }}>
                    {trade.symbol.replace("USDT", "/USDT")}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: "2px 6px",
                      borderRadius: 5,
                      background: isLong ? "var(--accent-green-dim)" : "var(--accent-red-dim)",
                      color: isLong ? "var(--accent-green)" : "var(--accent-red)",
                    }}
                  >
                    {trade.direction} {trade.leverage}x
                  </span>
                </div>
                <span
                  style={{
                    fontWeight: 800,
                    fontSize: 16,
                    color: isPositive ? "var(--accent-green)" : "var(--accent-red)",
                  }}
                >
                  {isPositive ? "+" : ""}${pnl.toFixed(2)}
                </span>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 4,
                  marginBottom: 8,
                }}
              >
                {[
                  { label: "Вход", value: `$${parseFloat(trade.entry_price).toLocaleString("en")}` },
                  { label: "Выход", value: trade.close_price ? `$${parseFloat(trade.close_price).toLocaleString("en")}` : "—" },
                  {
                    label: "Причина",
                    value: CLOSE_REASON_LABELS[trade.close_reason] || trade.close_reason || "—",
                  },
                ].map((item) => (
                  <div key={item.label}>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 2 }}>
                      {item.label}
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 500 }}>{item.value}</div>
                  </div>
                ))}
              </div>

              {closeDate && (
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {closeDate.toLocaleDateString("ru")} {closeDate.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })}
                </div>
              )}
            </motion.div>
          );
        })}

        {hasMore && trades.length > 0 && (
          <button
            className="btn btn-secondary"
            onClick={loadMore}
            disabled={loadingMore}
          >
            {loadingMore ? (
              <span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
            ) : (
              "Загрузить ещё"
            )}
          </button>
        )}
      </div>
    </div>
  );
}
