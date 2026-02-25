import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getAccountOverview } from "../api/index.js";
import { ProgressBar } from "../components/ProgressBar.jsx";

const PHASE_STEPS = [
  { phase: "EVALUATION", label: "Evaluation", step: 1, target: "+8%", desc: "Докажи свои навыки" },
  { phase: "VERIFICATION", label: "Verification", step: 2, target: "+5%", desc: "Подтверди стабильность" },
  { phase: "FUNDED", label: "Funded", step: 3, target: "∞", desc: "Торгуй на реальные деньги" },
];

export default function Challenge() {
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAccountOverview()
      .then(setAccount)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  if (!account) return null;

  const currentPhaseIdx = PHASE_STEPS.findIndex((s) => s.phase === account.phase);
  const profitPct = (
    ((parseFloat(account.current_balance) - parseFloat(account.initial_balance)) /
      parseFloat(account.initial_balance)) *
    100
  ).toFixed(2);

  const daysProgress = Math.min(
    (account.trading_days_count / account.min_trading_days) * 100,
    100
  );

  return (
    <div className="page">
      <div className="page-header">
        <h1>Прогресс челленджа</h1>
      </div>

      <div className="page-content">
        {/* Phase roadmap */}
        <div className="card">
          <h3 style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Путь трейдера
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {PHASE_STEPS.map((step, idx) => {
              const isCurrent = step.phase === account.phase;
              const isPassed = idx < currentPhaseIdx || (account.status === "PASSED" && isCurrent);
              const isFailed = account.status === "FAILED" && isCurrent;

              return (
                <div key={step.phase} style={{ display: "flex", gap: 14, paddingBottom: idx < 2 ? 0 : 0 }}>
                  {/* Line + circle */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 28 }}>
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: "50%",
                        border: `2px solid ${
                          isFailed
                            ? "var(--accent-red)"
                            : isPassed
                            ? "var(--accent-green)"
                            : isCurrent
                            ? "var(--accent-green)"
                            : "var(--text-muted)"
                        }`,
                        background: isPassed
                          ? "var(--accent-green)"
                          : isCurrent
                          ? "var(--accent-green-dim)"
                          : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 12,
                        fontWeight: 700,
                        color: isPassed ? "#000" : isCurrent ? "var(--accent-green)" : "var(--text-muted)",
                        flexShrink: 0,
                      }}
                    >
                      {isFailed ? "✕" : isPassed ? "✓" : step.step}
                    </div>
                    {idx < PHASE_STEPS.length - 1 && (
                      <div
                        style={{
                          width: 2,
                          flex: 1,
                          minHeight: 32,
                          background: isPassed ? "var(--accent-green)" : "var(--border)",
                          margin: "4px 0",
                        }}
                      />
                    )}
                  </div>

                  {/* Content */}
                  <div style={{ paddingBottom: idx < PHASE_STEPS.length - 1 ? 16 : 0, flex: 1 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 4,
                      }}
                    >
                      <span style={{ fontWeight: 700, fontSize: 15 }}>{step.label}</span>
                      <span
                        style={{
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 6,
                          background: isCurrent ? "var(--accent-green-dim)" : "var(--bg-secondary)",
                          color: isCurrent ? "var(--accent-green)" : "var(--text-muted)",
                          border: `1px solid ${isCurrent ? "var(--accent-green)33" : "var(--border)"}`,
                        }}
                      >
                        Цель {step.target}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>{step.desc}</p>

                    {isCurrent && account.status !== "FAILED" && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}
                      >
                        <ProgressBar
                          value={parseFloat(account.profit_progress_pct)}
                          max={100}
                          label="Прибыль"
                          sublabel={`${profitPct}% / +${account.profit_target_pct}%`}
                        />
                        <ProgressBar
                          value={daysProgress}
                          max={100}
                          label="Торговые дни"
                          sublabel={`${account.trading_days_count} / ${account.min_trading_days}`}
                        />
                      </motion.div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Rules card */}
        <div className="card">
          <h3 style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Правила
          </h3>
          {[
            {
              label: "Дневная просадка",
              value: `-${account.max_daily_drawdown_pct}%`,
              status: parseFloat(account.daily_drawdown_pct) <= -parseFloat(account.max_daily_drawdown_pct) * 0.8 ? "warn" : "ok",
              current: `${parseFloat(account.daily_drawdown_pct).toFixed(2)}%`,
            },
            {
              label: "Trailing просадка",
              value: `${account.max_trailing_drawdown_pct}%`,
              status: parseFloat(account.trailing_drawdown_pct) >= parseFloat(account.max_trailing_drawdown_pct) * 0.8 ? "warn" : "ok",
              current: `${parseFloat(account.trailing_drawdown_pct).toFixed(2)}%`,
            },
            {
              label: "Мин. торговых дней",
              value: `${account.min_trading_days}`,
              status: account.trading_days_count >= account.min_trading_days ? "done" : "pending",
              current: `${account.trading_days_count}/${account.min_trading_days}`,
            },
            {
              label: "Цель прибыли",
              value: `+${account.profit_target_pct}%`,
              status:
                parseFloat(account.profit_progress_pct) >= 100
                  ? "done"
                  : parseFloat(account.profit_progress_pct) >= 50
                  ? "progress"
                  : "pending",
              current: `${parseFloat(account.profit_progress_pct).toFixed(1)}%`,
            },
          ].map((rule) => (
            <div
              key={rule.label}
              className="row"
              style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}
            >
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{rule.label}</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Лимит: {rule.value}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 3 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{rule.current}</span>
                <span
                  style={{
                    fontSize: 10,
                    padding: "1px 6px",
                    borderRadius: 4,
                    background:
                      rule.status === "done"
                        ? "var(--accent-green-dim)"
                        : rule.status === "warn"
                        ? "var(--accent-red-dim)"
                        : rule.status === "progress"
                        ? "rgba(100,149,237,0.15)"
                        : "var(--bg-secondary)",
                    color:
                      rule.status === "done"
                        ? "var(--accent-green)"
                        : rule.status === "warn"
                        ? "var(--accent-red)"
                        : rule.status === "progress"
                        ? "#6495ed"
                        : "var(--text-muted)",
                  }}
                >
                  {rule.status === "done" ? "✓ Выполнено" : rule.status === "warn" ? "⚠ Лимит" : rule.status === "progress" ? "В процессе" : "Ожидание"}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Account info */}
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}>
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Начальный баланс</span>
            <span style={{ fontWeight: 600 }}>${parseFloat(account.initial_balance).toLocaleString("en")}</span>
          </div>
          <div className="row" style={{ marginBottom: 8 }}>
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Текущий баланс</span>
            <span style={{ fontWeight: 700, fontSize: 16 }}>
              ${parseFloat(account.current_balance).toLocaleString("en", { minimumFractionDigits: 2 })}
            </span>
          </div>
          {account.phase === "FUNDED" && (
            <div className="row">
              <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Profit Split</span>
              <span style={{ fontWeight: 600, color: "var(--accent-green)" }}>
                {account.profit_split_pct}% тебе
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
