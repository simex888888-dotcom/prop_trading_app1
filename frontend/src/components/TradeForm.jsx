import React, { useState, useEffect } from "react";
import { RiskCalculator } from "./RiskCalculator.jsx";
import { openTrade } from "../api/index.js";

const SYMBOLS = [
  { value: "BTCUSDT", label: "BTC/USDT" },
  { value: "ETHUSDT", label: "ETH/USDT" },
  { value: "SOLUSDT", label: "SOL/USDT" },
  { value: "BNBUSDT", label: "BNB/USDT" },
  { value: "XRPUSDT", label: "XRP/USDT" },
  { value: "DOGEUSDT", label: "DOGE/USDT" },
  { value: "TONUSDT", label: "TON/USDT" },
];

const LEVERAGE_OPTIONS = [1, 2, 3, 5, 7, 10];

export function TradeForm({ balance, prices, onSuccess, hapticFeedback }) {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [direction, setDirection] = useState("LONG");
  const [leverage, setLeverage] = useState(1);
  const [takeProfit, setTakeProfit] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const currentPrice = prices?.[symbol] ? parseFloat(prices[symbol]) : null;

  // Автоматически ставим дефолтные TP/SL при смене символа или направления
  useEffect(() => {
    if (!currentPrice) return;
    if (direction === "LONG") {
      setTakeProfit((currentPrice * 1.02).toFixed(getPrecision(symbol)));
      setStopLoss((currentPrice * 0.99).toFixed(getPrecision(symbol)));
    } else {
      setTakeProfit((currentPrice * 0.98).toFixed(getPrecision(symbol)));
      setStopLoss((currentPrice * 1.01).toFixed(getPrecision(symbol)));
    }
  }, [symbol, direction, currentPrice]);

  function getPrecision(sym) {
    if (sym === "BTCUSDT") return 1;
    if (sym === "ETHUSDT") return 2;
    if (["XRPUSDT", "DOGEUSDT", "TONUSDT"].includes(sym)) return 4;
    return 2;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!riskData) {
      setError("Заполните калькулятор риска");
      return;
    }
    if (!takeProfit || !stopLoss) {
      setError("Укажите Take Profit и Stop Loss");
      return;
    }

    hapticFeedback && hapticFeedback("impact", "medium");
    setLoading(true);

    try {
      const trade = await openTrade({
        symbol,
        direction,
        leverage,
        risk_pct: riskData.riskPct,
        take_profit: parseFloat(takeProfit),
        stop_loss: parseFloat(stopLoss),
      });
      hapticFeedback && hapticFeedback("notification", "success");
      onSuccess(trade);
    } catch (e) {
      setError(e.message);
      hapticFeedback && hapticFeedback("notification", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Symbol */}
      <div className="input-group">
        <label className="input-label">Торговая пара</label>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 6,
          }}
        >
          {SYMBOLS.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setSymbol(s.value)}
              style={{
                height: 40,
                borderRadius: 8,
                background: symbol === s.value ? "var(--accent-green)" : "var(--bg-secondary)",
                color: symbol === s.value ? "#000" : "var(--text-secondary)",
                fontWeight: 600,
                fontSize: 11,
                border: "1px solid var(--border)",
                transition: "all 0.15s",
              }}
            >
              {s.label.replace("/USDT", "")}
            </button>
          ))}
        </div>
      </div>

      {/* Current price */}
      {currentPrice && (
        <div className="card" style={{ padding: "10px 14px" }}>
          <div className="row">
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>
              Текущая цена {SYMBOLS.find((s) => s.value === symbol)?.label}
            </span>
            <span style={{ fontWeight: 700, fontSize: 16 }}>
              ${currentPrice.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
            </span>
          </div>
        </div>
      )}

      {/* Direction */}
      <div className="input-group">
        <label className="input-label">Направление</label>
        <div className="segment-control">
          <button
            type="button"
            className={`segment-btn ${direction === "LONG" ? "active green" : ""}`}
            onClick={() => setDirection("LONG")}
          >
            📈 LONG
          </button>
          <button
            type="button"
            className={`segment-btn ${direction === "SHORT" ? "active red" : ""}`}
            onClick={() => setDirection("SHORT")}
          >
            📉 SHORT
          </button>
        </div>
      </div>

      {/* Leverage */}
      <div className="input-group">
        <label className="input-label">Кредитное плечо</label>
        <div style={{ display: "flex", gap: 6 }}>
          {LEVERAGE_OPTIONS.map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => setLeverage(l)}
              style={{
                flex: 1,
                height: 40,
                borderRadius: 8,
                background: leverage === l ? "var(--accent-green)" : "var(--bg-secondary)",
                color: leverage === l ? "#000" : "var(--text-secondary)",
                fontWeight: 700,
                fontSize: 13,
                border: "1px solid var(--border)",
                transition: "all 0.15s",
              }}
            >
              {l}x
            </button>
          ))}
        </div>
      </div>

      {/* Take Profit */}
      <div className="input-group">
        <label className="input-label">Take Profit ($)</label>
        <input
          type="number"
          className="input-field"
          value={takeProfit}
          onChange={(e) => setTakeProfit(e.target.value)}
          placeholder="Цена закрытия с прибылью"
          step="any"
          inputMode="decimal"
          style={{ borderColor: takeProfit ? "var(--accent-green)" + "44" : "" }}
        />
      </div>

      {/* Stop Loss */}
      <div className="input-group">
        <label className="input-label">Stop Loss ($)</label>
        <input
          type="number"
          className="input-field"
          value={stopLoss}
          onChange={(e) => setStopLoss(e.target.value)}
          placeholder="Цена закрытия с убытком"
          step="any"
          inputMode="decimal"
          style={{ borderColor: stopLoss ? "var(--accent-red)" + "44" : "" }}
        />
      </div>

      {/* Risk Calculator */}
      <div className="card">
        <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12 }}>
          🧮 КАЛЬКУЛЯТОР РИСКА
        </h3>
        <RiskCalculator
          balance={balance}
          entryPrice={currentPrice || 0}
          stopLoss={parseFloat(stopLoss) || 0}
          direction={direction}
          leverage={leverage}
          onResult={setRiskData}
        />
      </div>

      {error && (
        <div
          style={{
            background: "var(--accent-red-dim)",
            border: "1px solid rgba(255,68,68,0.3)",
            borderRadius: 10,
            padding: "10px 14px",
            color: "var(--accent-red)",
            fontSize: 13,
          }}
        >
          ⚠️ {error}
        </div>
      )}

      <button
        type="submit"
        className={`btn ${direction === "LONG" ? "btn-primary" : "btn-danger"}`}
        disabled={loading || !currentPrice || !riskData}
        style={{
          background: direction === "SHORT" ? "var(--accent-red)" : undefined,
          color: direction === "SHORT" ? "#fff" : undefined,
        }}
      >
        {loading ? (
          <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
        ) : (
          `${direction === "LONG" ? "📈 Открыть LONG" : "📉 Открыть SHORT"} · ${leverage}x`
        )}
      </button>
    </form>
  );
}
