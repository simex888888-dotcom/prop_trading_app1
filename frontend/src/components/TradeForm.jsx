import React, { useState, useEffect } from "react";
import { RiskCalculator } from "./RiskCalculator.jsx";
import { openTrade } from "../api/index.js";

const SYMBOLS = [
  { value: "BTCUSDT",  label: "BTC/USDT" },
  { value: "ETHUSDT",  label: "ETH/USDT" },
  { value: "SOLUSDT",  label: "SOL/USDT" },
  { value: "BNBUSDT",  label: "BNB/USDT" },
  { value: "XRPUSDT",  label: "XRP/USDT" },
  { value: "DOGEUSDT", label: "DOGE/USDT" },
  { value: "TONUSDT",  label: "TON/USDT" },
  { value: "ADAUSDT",  label: "ADA/USDT" },
  { value: "AVAXUSDT", label: "AVAX/USDT" },
  { value: "DOTUSDT",  label: "DOT/USDT" },
  { value: "LINKUSDT", label: "LINK/USDT" },
  { value: "MATICUSDT",label: "MATIC/USDT" },
  { value: "LTCUSDT",  label: "LTC/USDT" },
  { value: "UNIUSDT",  label: "UNI/USDT" },
  { value: "ATOMUSDT", label: "ATOM/USDT" },
  { value: "NEARUSDT", label: "NEAR/USDT" },
  { value: "APTUSDT",  label: "APT/USDT" },
  { value: "OPUSDT",   label: "OP/USDT" },
  { value: "ARBUSDT",  label: "ARB/USDT" },
  { value: "SUIUSDT",  label: "SUI/USDT" },
  { value: "INJUSDT",  label: "INJ/USDT" },
  { value: "TIAUSDT",  label: "TIA/USDT" },
  { value: "SEIUSDT",  label: "SEI/USDT" },
  { value: "STXUSDT",  label: "STX/USDT" },
  { value: "RUNEUSDT", label: "RUNE/USDT" },
  { value: "FTMUSDT",  label: "FTM/USDT" },
  { value: "AAVEUSDT", label: "AAVE/USDT" },
  { value: "SANDUSDT", label: "SAND/USDT" },
  { value: "MANAUSDT", label: "MANA/USDT" },
  { value: "GALAUSDT", label: "GALA/USDT" },
];

const LEVERAGE_OPTIONS = [1, 2, 3, 5, 7, 10, 15, 20, 25, 50];

function getPrecision(sym) {
  if (sym === "BTCUSDT") return 1;
  if (sym === "ETHUSDT") return 2;
  if (["XRPUSDT", "DOGEUSDT", "TONUSDT", "ADAUSDT", "MATICUSDT", "SANDUSDT", "MANAUSDT", "GALAUSDT", "SEIUSDT"].includes(sym)) return 4;
  return 2;
}

// Quick TP/SL % presets
const TP_PRESETS_LONG  = [1, 2, 3, 5, 10];
const SL_PRESETS_LONG  = [0.5, 1, 2, 3, 5];
const TP_PRESETS_SHORT = [1, 2, 3, 5, 10];
const SL_PRESETS_SHORT = [0.5, 1, 2, 3, 5];

export function TradeForm({ balance, prices, onSuccess, hapticFeedback }) {
  const [symbol, setSymbol]       = useState("BTCUSDT");
  const [direction, setDirection] = useState("LONG");
  const [leverage, setLeverage]   = useState(1);
  const [takeProfit, setTakeProfit] = useState("");
  const [stopLoss, setStopLoss]     = useState("");
  const [riskData, setRiskData]     = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  // position size mode: "risk" (RiskCalculator) or "usdt" (fixed USDT)
  const [sizeMode, setSizeMode] = useState("risk");
  const [usdtAmount, setUsdtAmount] = useState("");
  // entry price override (for limit orders — used for TP/SL calculation reference)
  const [entryPrice, setEntryPrice] = useState("");

  const currentPrice = prices?.[symbol] ? parseFloat(prices[symbol]) : null;
  const refPrice = entryPrice ? parseFloat(entryPrice) : currentPrice;

  // Auto-set default TP/SL and entry price when symbol/direction changes
  useEffect(() => {
    if (!currentPrice) return;
    setEntryPrice(currentPrice.toFixed(getPrecision(symbol)));
    if (direction === "LONG") {
      setTakeProfit((currentPrice * 1.02).toFixed(getPrecision(symbol)));
      setStopLoss((currentPrice * 0.99).toFixed(getPrecision(symbol)));
    } else {
      setTakeProfit((currentPrice * 0.98).toFixed(getPrecision(symbol)));
      setStopLoss((currentPrice * 1.01).toFixed(getPrecision(symbol)));
    }
  }, [symbol, direction, currentPrice]);

  function applyTpPreset(pct) {
    if (!refPrice) return;
    const val = direction === "LONG"
      ? (refPrice * (1 + pct / 100)).toFixed(getPrecision(symbol))
      : (refPrice * (1 - pct / 100)).toFixed(getPrecision(symbol));
    setTakeProfit(val);
  }

  function applySlPreset(pct) {
    if (!refPrice) return;
    const val = direction === "LONG"
      ? (refPrice * (1 - pct / 100)).toFixed(getPrecision(symbol))
      : (refPrice * (1 + pct / 100)).toFixed(getPrecision(symbol));
    setStopLoss(val);
  }

  function adjustEntry(pct) {
    const base = entryPrice ? parseFloat(entryPrice) : currentPrice;
    if (!base) return;
    setEntryPrice((base * (1 + pct / 100)).toFixed(getPrecision(symbol)));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (sizeMode === "risk" && !riskData) {
      setError("Заполните калькулятор риска");
      return;
    }
    if (sizeMode === "usdt" && (!usdtAmount || parseFloat(usdtAmount) <= 0)) {
      setError("Укажите размер позиции в USDT");
      return;
    }
    if (!takeProfit || !stopLoss) {
      setError("Укажите Take Profit и Stop Loss");
      return;
    }

    hapticFeedback && hapticFeedback("impact", "medium");
    setLoading(true);

    try {
      const payload = {
        symbol,
        direction,
        leverage,
        take_profit: parseFloat(takeProfit),
        stop_loss: parseFloat(stopLoss),
      };
      if (sizeMode === "risk") {
        payload.risk_pct = riskData.riskPct;
      } else {
        payload.usdt_amount = parseFloat(usdtAmount);
      }
      const trade = await openTrade(payload);
      hapticFeedback && hapticFeedback("notification", "success");
      onSuccess(trade);
    } catch (e) {
      setError(e.message);
      hapticFeedback && hapticFeedback("notification", "error");
    } finally {
      setLoading(false);
    }
  }

  const isLong = direction === "LONG";
  const tpPresets = isLong ? TP_PRESETS_LONG : TP_PRESETS_SHORT;
  const slPresets = isLong ? SL_PRESETS_LONG : SL_PRESETS_SHORT;

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* Symbol — scrollable grid */}
      <div className="input-group">
        <label className="input-label">Торговая пара</label>
        <div style={{ overflowX: "auto", paddingBottom: 4 }}>
          <div style={{ display: "flex", gap: 6, width: "max-content" }}>
            {SYMBOLS.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setSymbol(s.value)}
                style={{
                  height: 36,
                  padding: "0 10px",
                  borderRadius: 8,
                  background: symbol === s.value ? "var(--accent-green)" : "var(--bg-secondary)",
                  color: symbol === s.value ? "#000" : "var(--text-secondary)",
                  fontWeight: 600,
                  fontSize: 11,
                  border: "1px solid var(--border)",
                  whiteSpace: "nowrap",
                  transition: "all 0.15s",
                }}
              >
                {s.label.replace("/USDT", "")}
              </button>
            ))}
          </div>
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
          <button type="button" className={`segment-btn ${isLong ? "active green" : ""}`} onClick={() => setDirection("LONG")}>
            📈 LONG
          </button>
          <button type="button" className={`segment-btn ${!isLong ? "active red" : ""}`} onClick={() => setDirection("SHORT")}>
            📉 SHORT
          </button>
        </div>
      </div>

      {/* Leverage */}
      <div className="input-group">
        <label className="input-label">Кредитное плечо</label>
        <div style={{ overflowX: "auto", paddingBottom: 4 }}>
          <div style={{ display: "flex", gap: 6, width: "max-content" }}>
            {LEVERAGE_OPTIONS.map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLeverage(l)}
                style={{
                  height: 38,
                  minWidth: 44,
                  padding: "0 8px",
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
      </div>

      {/* Entry price with ± buttons */}
      <div className="input-group">
        <label className="input-label">Цена входа (для TP/SL расчёта)</label>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <button type="button" onClick={() => adjustEntry(-0.1)} style={adjBtnStyle}>−</button>
          <input
            type="number"
            className="input-field"
            value={entryPrice}
            onChange={(e) => setEntryPrice(e.target.value)}
            placeholder="Цена входа"
            step="any"
            inputMode="decimal"
            style={{ flex: 1 }}
          />
          <button type="button" onClick={() => adjustEntry(0.1)} style={adjBtnStyle}>+</button>
        </div>
        <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
          {[-1, -0.5, 0.5, 1].map((pct) => (
            <button key={pct} type="button" onClick={() => adjustEntry(pct)}
              style={{ ...presetBtnStyle, flex: 1, fontSize: 10 }}>
              {pct > 0 ? `+${pct}%` : `${pct}%`}
            </button>
          ))}
          <button type="button" onClick={() => currentPrice && setEntryPrice(currentPrice.toFixed(getPrecision(symbol)))}
            style={{ ...presetBtnStyle, flex: 1, fontSize: 10, color: "var(--accent-green)" }}>
            Рыночная
          </button>
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
        <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
          {tpPresets.map((pct) => (
            <button key={pct} type="button" onClick={() => applyTpPreset(pct)}
              style={{ ...presetBtnStyle, flex: 1, color: "var(--accent-green)" }}>
              +{pct}%
            </button>
          ))}
        </div>
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
        <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
          {slPresets.map((pct) => (
            <button key={pct} type="button" onClick={() => applySlPreset(pct)}
              style={{ ...presetBtnStyle, flex: 1, color: "var(--accent-red)" }}>
              −{pct}%
            </button>
          ))}
        </div>
      </div>

      {/* Position size mode toggle */}
      <div className="input-group">
        <label className="input-label">Размер позиции</label>
        <div className="segment-control" style={{ marginBottom: 10 }}>
          <button type="button" className={`segment-btn ${sizeMode === "risk" ? "active" : ""}`}
            onClick={() => setSizeMode("risk")}>
            % Риска
          </button>
          <button type="button" className={`segment-btn ${sizeMode === "usdt" ? "active" : ""}`}
            onClick={() => setSizeMode("usdt")}>
            USDT сумма
          </button>
        </div>

        {sizeMode === "risk" ? (
          <div className="card">
            <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12 }}>
              🧮 КАЛЬКУЛЯТОР РИСКА
            </h3>
            <RiskCalculator
              balance={balance}
              entryPrice={refPrice || 0}
              stopLoss={parseFloat(stopLoss) || 0}
              direction={direction}
              leverage={leverage}
              onResult={setRiskData}
            />
          </div>
        ) : (
          <div>
            <input
              type="number"
              className="input-field"
              value={usdtAmount}
              onChange={(e) => setUsdtAmount(e.target.value)}
              placeholder="Например: 100"
              step="any"
              inputMode="decimal"
            />
            <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
              {[10, 25, 50, 100].map((pct) => {
                const amt = balance ? (balance * pct / 100).toFixed(2) : "";
                return (
                  <button key={pct} type="button"
                    onClick={() => amt && setUsdtAmount(amt)}
                    style={{ ...presetBtnStyle, flex: 1 }}>
                    {pct}%
                    {amt && <span style={{ display: "block", fontSize: 9, opacity: 0.7 }}>${amt}</span>}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div style={{
          background: "var(--accent-red-dim)",
          border: "1px solid rgba(255,68,68,0.3)",
          borderRadius: 10,
          padding: "10px 14px",
          color: "var(--accent-red)",
          fontSize: 13,
        }}>
          ⚠️ {error}
        </div>
      )}

      <button
        type="submit"
        className={`btn ${isLong ? "btn-primary" : "btn-danger"}`}
        disabled={loading || !currentPrice || (sizeMode === "risk" && !riskData)}
        style={{
          background: !isLong ? "var(--accent-red)" : undefined,
          color: !isLong ? "#fff" : undefined,
        }}
      >
        {loading ? (
          <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
        ) : (
          `${isLong ? "📈 Открыть LONG" : "📉 Открыть SHORT"} · ${leverage}x`
        )}
      </button>
    </form>
  );
}

const adjBtnStyle = {
  width: 40,
  height: 40,
  borderRadius: 8,
  background: "var(--bg-secondary)",
  border: "1px solid var(--border)",
  color: "var(--text-primary)",
  fontSize: 20,
  fontWeight: 700,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  flexShrink: 0,
};

const presetBtnStyle = {
  height: 30,
  borderRadius: 6,
  background: "var(--bg-secondary)",
  border: "1px solid var(--border)",
  color: "var(--text-secondary)",
  fontSize: 11,
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.15s",
};
