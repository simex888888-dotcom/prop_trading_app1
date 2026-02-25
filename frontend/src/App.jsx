import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import { useTelegram } from "./hooks/useTelegram.js";
import { authTelegram } from "./api/index.js";
import { ErrorBoundary } from "./components/ErrorBoundary.jsx";

import Dashboard from "./pages/Dashboard.jsx";
import Trade from "./pages/Trade.jsx";
import History from "./pages/History.jsx";
import Challenge from "./pages/Challenge.jsx";
import Leaderboard from "./pages/Leaderboard.jsx";

function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const items = [
    { path: "/", label: "Главная", icon: "📊" },
    { path: "/challenge", label: "Челлендж", icon: "🎯" },
    { path: "/leaderboard", label: "Рейтинг", icon: "🏆" },
    { path: "/history", label: "История", icon: "📋" },
  ];

  // Не показываем BottomNav на странице Trade
  if (location.pathname === "/trade") return null;

  return (
    <nav className="bottom-nav">
      {items.map((item) => (
        <button
          key={item.path}
          className={`nav-item ${location.pathname === item.path ? "active" : ""}`}
          onClick={() => navigate(item.path)}
        >
          <span style={{ fontSize: 20 }}>{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

function PageWrapper({ children }) {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -10 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
        style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  const { isReady, initData, colorScheme, hapticFeedback } = useTelegram();
  const [authStatus, setAuthStatus] = useState("loading"); // loading | ok | error
  const [authError, setAuthError] = useState(null);

  useEffect(() => {
    if (!isReady) return;

    async function doAuth() {
      try {
        // В dev-режиме используем мок-токен
        if (initData === "dev_mode") {
          const mockToken = localStorage.getItem("auth_token");
          if (!mockToken) {
            // Попробуем авторизоваться с dev-данными
            // Для дев-среды бэкенд должен принять специальный токен
            localStorage.setItem("auth_token", "dev_token_placeholder");
          }
          setAuthStatus("ok");
          return;
        }

        const existingToken = localStorage.getItem("auth_token");

        // Всегда переавторизуемся при старте, чтобы обновить сессию
        await authTelegram(initData);
        setAuthStatus("ok");
      } catch (e) {
        setAuthError(e.message);
        setAuthStatus("error");
      }
    }

    doAuth();
  }, [isReady, initData]);

  // Применяем тему Telegram
  useEffect(() => {
    if (colorScheme === "light") {
      document.documentElement.style.setProperty("--bg-primary", "#f5f5f5");
      document.documentElement.style.setProperty("--bg-secondary", "#ffffff");
      document.documentElement.style.setProperty("--bg-card", "#ffffff");
      document.documentElement.style.setProperty("--text-primary", "#111111");
      document.documentElement.style.setProperty("--text-secondary", "#555555");
      document.documentElement.style.setProperty("--border", "rgba(0,0,0,0.1)");
    }
  }, [colorScheme]);

  if (!isReady || authStatus === "loading") {
    return (
      <div className="loading-screen">
        <div style={{ fontSize: 40, marginBottom: 8 }}>📈</div>
        <div className="spinner" />
        <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>Загрузка...</span>
      </div>
    );
  }

  if (authStatus === "error") {
    return (
      <div className="loading-screen">
        <div style={{ fontSize: 40 }}>🔒</div>
        <h2 style={{ fontSize: 16, textAlign: "center" }}>Ошибка авторизации</h2>
        <p style={{ color: "var(--text-secondary)", textAlign: "center", fontSize: 13 }}>
          {authError}
        </p>
        <button
          className="btn btn-primary"
          style={{ maxWidth: 200 }}
          onClick={() => window.location.reload()}
        >
          Повторить
        </button>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
          <Routes>
            <Route
              path="/"
              element={
                <PageWrapper>
                  <Dashboard hapticFeedback={hapticFeedback} />
                </PageWrapper>
              }
            />
            <Route
              path="/trade"
              element={
                <PageWrapper>
                  <Trade hapticFeedback={hapticFeedback} />
                </PageWrapper>
              }
            />
            <Route
              path="/history"
              element={
                <PageWrapper>
                  <History />
                </PageWrapper>
              }
            />
            <Route
              path="/challenge"
              element={
                <PageWrapper>
                  <Challenge />
                </PageWrapper>
              }
            />
            <Route
              path="/leaderboard"
              element={
                <PageWrapper>
                  <Leaderboard />
                </PageWrapper>
              }
            />
          </Routes>
          <BottomNav />
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
