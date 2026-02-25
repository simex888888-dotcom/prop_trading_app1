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
          <div style={{ fontSize: 56 }}>💔</div>

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
                "🚀 Начать заново"
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
