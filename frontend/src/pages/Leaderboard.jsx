import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getLeaderboard } from "../api/index.js";

const MEDAL = ["🥇", "🥈", "🥉"];

const PHASE_SHORT = {
  EVALUATION: "Eval",
  VERIFICATION: "Verif",
  FUNDED: "Funded",
};

export default function Leaderboard() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getLeaderboard()
      .then(setEntries)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

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
        <h1>🏆 Рейтинг трейдеров</h1>
      </div>

      <div className="page-content">
        {error && (
          <div style={{ color: "var(--accent-red)", textAlign: "center" }}>{error}</div>
        )}

        {!error && entries.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 20px" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🏜️</div>
            <p style={{ color: "var(--text-secondary)" }}>Пока нет данных. Торгуй первым!</p>
          </div>
        )}

        {entries.map((entry, i) => {
          const profit = parseFloat(entry.profit_pct);
          const isPositive = profit >= 0;
          const isMedal = i < 3;

          return (
            <motion.div
              key={entry.user_id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              style={{
                background: isMedal ? "var(--bg-card)" : "var(--bg-secondary)",
                border: `1px solid ${isMedal ? "rgba(255,215,0,0.15)" : "var(--border)"}`,
                borderRadius: 14,
                padding: "12px 14px",
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              {/* Rank */}
              <div
                style={{
                  width: 32,
                  height: 32,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: isMedal ? 20 : 14,
                  fontWeight: 700,
                  color: "var(--text-muted)",
                  flexShrink: 0,
                }}
              >
                {isMedal ? MEDAL[i] : `#${entry.rank}`}
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: 14,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {entry.display_name}
                  </span>
                  <span className={`phase-badge phase-${entry.phase}`} style={{ flexShrink: 0 }}>
                    {PHASE_SHORT[entry.phase] || entry.phase}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 10, fontSize: 11, color: "var(--text-secondary)" }}>
                  <span>WR: {parseFloat(entry.win_rate).toFixed(1)}%</span>
                  <span>Сделок: {entry.total_trades}</span>
                  <span>Дней: {entry.trading_days_count}</span>
                </div>
              </div>

              {/* PnL */}
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div
                  style={{
                    fontWeight: 800,
                    fontSize: 15,
                    color: isPositive ? "var(--accent-green)" : "var(--accent-red)",
                  }}
                >
                  {isPositive ? "+" : ""}
                  {profit.toFixed(2)}%
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  ${parseFloat(entry.current_balance).toLocaleString("en", { minimumFractionDigits: 0 })}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
