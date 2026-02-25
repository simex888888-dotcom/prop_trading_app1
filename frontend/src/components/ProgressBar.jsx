import React from "react";

export function ProgressBar({ value, max = 100, label, sublabel, color = "green" }) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  const barColor = color === "green" ? "var(--accent-green)" : "var(--accent-red)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {(label || sublabel) && (
        <div className="row">
          {label && <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{label}</span>}
          {sublabel && <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 600 }}>{sublabel}</span>}
        </div>
      )}
      <div
        style={{
          height: 6,
          background: "var(--bg-secondary)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: barColor,
            borderRadius: 3,
            transition: "width 0.5s ease",
            boxShadow: pct > 0 ? `0 0 8px ${barColor}60` : "none",
          }}
        />
      </div>
    </div>
  );
}
