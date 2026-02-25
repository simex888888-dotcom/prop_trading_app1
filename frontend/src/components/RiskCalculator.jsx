import React, { useEffect, useState } from "react";

const LEVERAGE_OPTIONS = [1, 2, 3, 5, 7, 10];

export function RiskCalculator({ balance, entryPrice, stopLoss, direction, leverage, onResult }) {
  const [riskPct, setRiskPct] = useState("1");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    calculate();
  }, [riskPct, balance, entryPrice, stopLoss, direction, leverage]);

  function calculate() {
    setError(null);
    const rp = parseFloat(riskPct);
    const ep = parseFloat(entryPrice);
    const sl = parseFloat(stopLoss);
    const bal = parseFloat(balance);

    if (!rp || !ep || !sl || !bal) {
      setResult(null);
      return;
    }

    if (isNaN(rp) || rp <= 0 || rp > 10) {
      setError("Риск: 0.1–10%");
      setResult(null);
      return;
    }

    let stopDistance;
    if (direction === "LONG") {
      stopDistance = ep - sl;
    } else {
      stopDistance = sl - ep;
    }

    if (stopDistance <= 0) {
      setError("Stop loss не корректен для выбранного направления");
      setResult(null);
      return;
    }

    const riskAmount = bal * rp / 100;
    const positionSize = riskAmount / stopDistance;
    const notionalValue = positionSize * ep;
    const marginUsed = notionalValue / leverage;

    if (marginUsed > bal) {
      setError("Недостаточно средств для этого размера позиции");
      setResult(null);
      return;
    }

    const res = {
      positionSize: positionSize.toFixed(6),
      notionalValue: notionalValue.toFixed(2),
      marginUsed: marginUsed.toFixed(2),
      riskAmount: riskAmount.toFixed(2),
    };
    setResult(res);
    onResult && onResult({ ...res, riskPct: rp });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="input-group">
        <label className="input-label">Риск от депозита (%)</label>
        <div style={{ display: "flex", gap: 6 }}>
          {["0.5", "1", "2", "3", "5"].map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setRiskPct(v)}
              style={{
                flex: 1,
                height: 36,
                borderRadius: 8,
                background: riskPct === v ? "var(--accent-green)" : "var(--bg-secondary)",
                color: riskPct === v ? "#000" : "var(--text-secondary)",
                fontWeight: 600,
                fontSize: 13,
                border: "1px solid var(--border)",
                transition: "all 0.15s",
              }}
            >
              {v}%
            </button>
          ))}
        </div>
        <input
          type="number"
          className="input-field"
          value={riskPct}
          onChange={(e) => setRiskPct(e.target.value)}
          placeholder="Или введите вручную"
          min="0.1"
          max="10"
          step="0.1"
        />
      </div>

      {error && (
        <div style={{ color: "var(--accent-red)", fontSize: 12, padding: "8px 12px", background: "var(--accent-red-dim)", borderRadius: 8 }}>
          ⚠️ {error}
        </div>
      )}

      {result && !error && (
        <div className="card" style={{ padding: 12, gap: 8, display: "flex", flexDirection: "column" }}>
          <div className="row">
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Размер риска</span>
            <span style={{ color: "var(--accent-red)", fontWeight: 600 }}>${result.riskAmount}</span>
          </div>
          <div className="row">
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Размер позиции</span>
            <span style={{ fontWeight: 600 }}>{result.positionSize}</span>
          </div>
          <div className="row">
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Объём сделки</span>
            <span style={{ fontWeight: 600 }}>${parseFloat(result.notionalValue).toLocaleString("en", { minimumFractionDigits: 2 })}</span>
          </div>
          <div className="row">
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Маржа</span>
            <span style={{ fontWeight: 600 }}>${parseFloat(result.marginUsed).toLocaleString("en", { minimumFractionDigits: 2 })}</span>
          </div>
        </div>
      )}
    </div>
  );
}
