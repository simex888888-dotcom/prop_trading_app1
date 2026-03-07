import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { restartAccount } from "../api/index.js";

export function FailedOverlay({ account, onRestarted }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!account || account.status !== "FAILED") return null;

  const reasonText = {
    DAILY_DRAWDOWN_EXCEEDED: "Превышена дневная просадка (-5%)",
    TRAILING_DRAWDOWN_EXCEEDED: "Превышена максимальная просадка (-10%)",
  }[account.fail_reason] || "Нарушение правил торговли";

  async function handleRestart() {
    setLoading(true);
    setError(null);
    try {
      const result = await restartAccount();
      onRestarted(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.92)",
          zIndex: 200,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        <motion.div
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
          style={{
            background: "var(--bg-card)",
            borderRadius: 24,
            padding: 28,
            width: "100%",
            maxWidth: 360,
            border: "1px solid rgba(255,68,68,0.3)",
            display: "flex",
            flexDirection: "column",
            gap: 20,
            alignItems: "center",
          }}
        >
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="#FF4757" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            <line x1="12" y1="12" x2="12" y2="12.01" stroke="#FF4757" strokeWidth="3"/>
          </svg>

          <div style={{ textAlign: "center" }}>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 8 }}>
              Аккаунт заблокирован
            </h2>
            <div
              style={{
                background: "var(--accent-red-dim)",
                border: "1px solid rgba(255,68,68,0.3)",
                borderRadius: 10,
                padding: "10px 14px",
                marginBottom: 12,
              }}
            >
              <p style={{ color: "var(--accent-red)", fontWeight: 600, fontSize: 14 }}>
                {reasonText}
              </p>
            </div>
            {account.fail_detail && (
              <p style={{ color: "var(--text-secondary)", fontSize: 13, lineHeight: 1.6 }}>
                {account.fail_detail}
              </p>
            )}
          </div>

          <div
            style={{
              width: "100%",
              background: "var(--bg-secondary)",
              borderRadius: 12,
              padding: 14,
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <div className="row">
              <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Попытка</span>
              <span style={{ fontWeight: 600 }}>#{account.attempt_number}</span>
            </div>
            <div className="row">
              <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Фаза</span>
              <span className={`phase-badge phase-${account.phase}`}>{account.phase}</span>
            </div>
            {account.failed_at && (
              <div className="row">
                <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Дата</span>
                <span style={{ fontSize: 12 }}>
                  {new Date(account.failed_at).toLocaleDateString("ru")}
                </span>
              </div>
            )}
          </div>

          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
            <p style={{ color: "var(--text-secondary)", fontSize: 12, textAlign: "center" }}>
              Аккаунт сохранён в истории. Новая попытка — новый счёт $10,000.
            </p>

            {error && (
              <div style={{ color: "var(--accent-red)", fontSize: 12, textAlign: "center" }}>
                {error}
              </div>
            )}

            <button
              className="btn btn-primary"
              onClick={handleRestart}
              disabled={loading}
            >
              {loading ? (
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
              ) : (
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
                    <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
                    <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
                    <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
                  </svg>
                  Начать заново
                </span>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
