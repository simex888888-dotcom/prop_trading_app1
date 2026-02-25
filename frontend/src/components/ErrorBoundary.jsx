import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100vh",
            padding: 24,
            gap: 16,
            background: "#0d0d0d",
            color: "#fff",
          }}
        >
          <div style={{ fontSize: 48 }}>⚠️</div>
          <h2 style={{ fontSize: 18, fontWeight: 700, textAlign: "center" }}>
            Что-то пошло не так
          </h2>
          <p style={{ color: "#888", fontSize: 13, textAlign: "center" }}>
            {this.state.error?.message || "Неизвестная ошибка"}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              background: "#00ff88",
              color: "#000",
              border: "none",
              borderRadius: 10,
              padding: "12px 24px",
              fontWeight: 700,
              fontSize: 15,
              cursor: "pointer",
              marginTop: 8,
            }}
          >
            Перезагрузить
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
