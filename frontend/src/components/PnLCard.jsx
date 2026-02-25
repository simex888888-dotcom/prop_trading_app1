import React from "react";

export function PnLCard({ pnl, pnlPct, label = "Нереализованный PnL", size = "large" }) {
  const isPositive = parseFloat(pnl) >= 0;
  const isZero = parseFloat(pnl) === 0;

  const bg = isZero
    ? "rgba(255,255,255,0.05)"
    : isPositive
    ? "rgba(0, 255, 136, 0.08)"
    : "rgba(255, 68, 68, 0.08)";

  const color = isZero
    ? "var(--text-secondary)"
    : isPositive
    ? "var(--accent-green)"
    : "var(--accent-red)";

  const sign = isPositive && !isZero ? "+" : "";
  const formattedPnl = `${sign}$${Math.abs(parseFloat(pnl)).toLocaleString("en", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

  const displayPnl = parseFloat(pnl) < 0
    ? `-$${Math.abs(parseFloat(pnl)).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : formattedPnl;

  const fontSizeMap = { large: 32, medium: 22, small: 16 };
  const pctSizeMap = { large: 15, medium: 13, small: 12 };

  return (
    <div
      style={{
        background: bg,
        border: `1px solid ${isZero ? "var(--border)" : color + "33"}`,
        borderRadius: "var(--radius)",
        padding: size === "large" ? "20px 16px" : "12px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <span style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
        {label}
      </span>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <span
          style={{
            fontSize: fontSizeMap[size],
            fontWeight: 800,
            color,
            letterSpacing: "-0.5px",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {displayPnl}
        </span>
        {pnlPct !== undefined && (
          <span
            style={{
              fontSize: pctSizeMap[size],
              fontWeight: 600,
              color,
              opacity: 0.8,
            }}
          >
            {sign}{parseFloat(pnlPct) < 0 ? "" : ""}{parseFloat(pnlPct).toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  );
}
