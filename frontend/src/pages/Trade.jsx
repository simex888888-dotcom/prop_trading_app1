import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getAccountOverview, getPrices } from "../api/index.js";
import { TradeForm } from "../components/TradeForm.jsx";

export default function Trade({ hapticFeedback }) {
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [overview, pricesData] = await Promise.all([
          getAccountOverview(),
          getPrices(),
        ]);
        setAccount(overview);
        setPrices(pricesData.prices || {});
      } catch (e) {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();

    // Обновляем цены каждые 10 секунд
    const interval = setInterval(async () => {
      try {
        const pricesData = await getPrices();
        setPrices(pricesData.prices || {});
      } catch {}
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  function handleSuccess(trade) {
    setSuccess(trade);
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  if (success) {
    const isLong = success.direction === "LONG";
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="page"
        style={{ alignItems: "center", justifyContent: "center", padding: 24, gap: 20 }}
      >
        <div style={{ fontSize: 64 }}>{isLong ? "📈" : "📉"}</div>
        <h2 style={{ fontSize: 22, fontWeight: 800, textAlign: "center" }}>
          Позиция открыта!
        </h2>
        <div className="card" style={{ width: "100%" }}>
          {[
            { label: "Пара", value: success.symbol.replace("USDT", "/USDT") },
            { label: "Направление", value: `${success.direction} ${success.leverage}x` },
            { label: "Цена входа", value: `$${parseFloat(success.entry_price).toLocaleString("en")}` },
            { label: "Take Profit", value: `$${parseFloat(success.take_profit).toLocaleString("en")}`, color: "var(--accent-green)" },
            { label: "Stop Loss", value: `$${parseFloat(success.stop_loss).toLocaleString("en")}`, color: "var(--accent-red)" },
            { label: "Маржа", value: `$${parseFloat(success.margin_used).toLocaleString("en", { minimumFractionDigits: 2 })}` },
          ].map((item) => (
            <div key={item.label} className="row" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>{item.label}</span>
              <span style={{ fontWeight: 600, color: item.color || "var(--text-primary)" }}>{item.value}</span>
            </div>
          ))}
        </div>
        <div style={{ width: "100%", display: "flex", gap: 10 }}>
          <button
            className="btn btn-secondary"
            style={{ flex: 1 }}
            onClick={() => setSuccess(null)}
          >
            Ещё сделка
          </button>
          <button
            className="btn btn-primary"
            style={{ flex: 1 }}
            onClick={() => navigate("/")}
          >
            На главную
          </button>
        </div>
      </motion.div>
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
        <h1>Открыть сделку</h1>
      </div>

      {account && (
        <div
          style={{
            margin: "12px 16px 0",
            background: "var(--bg-card)",
            borderRadius: 10,
            padding: "10px 14px",
          }}
        >
          <div className="row">
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Доступный баланс</span>
            <span style={{ fontWeight: 700, fontSize: 16, color: "var(--accent-green)" }}>
              ${parseFloat(account.current_balance).toLocaleString("en", { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      )}

      <div className="page-content" style={{ paddingTop: 12 }}>
        {account && (
          <TradeForm
            balance={parseFloat(account.current_balance)}
            prices={prices}
            onSuccess={handleSuccess}
            hapticFeedback={hapticFeedback}
          />
        )}
      </div>
    </div>
  );
}
