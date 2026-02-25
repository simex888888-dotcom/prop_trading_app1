const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

function getToken() {
  return localStorage.getItem("auth_token") || "";
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getToken()}`,
  };
}

async function request(method, path, body = null) {
  const options = {
    method,
    headers: authHeaders(),
  };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${BASE_URL}${path}`, options);

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

// Auth
export async function authTelegram(initData) {
  const response = await fetch(`${BASE_URL}/auth/telegram`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Ошибка авторизации");
  }
  const data = await response.json();
  localStorage.setItem("auth_token", data.token);
  return data;
}

// Account
export async function getAccountOverview() {
  return request("GET", "/account/overview");
}

export async function getTradeHistory(limit = 50, offset = 0) {
  return request("GET", `/account/history?limit=${limit}&offset=${offset}`);
}

export async function restartAccount() {
  return request("POST", "/account/restart");
}

// Trading
export async function getPrices() {
  return request("GET", "/trading/prices");
}

export async function openTrade(data) {
  return request("POST", "/trading/open", data);
}

export async function closeTrade(tradeId) {
  return request("POST", "/trading/close", { trade_id: tradeId });
}

export async function getOpenTrades() {
  return request("GET", "/trading/open");
}

export async function checkTpSl() {
  return request("POST", "/trading/check-tpsl");
}

// Leaderboard
export async function getLeaderboard() {
  return request("GET", "/leaderboard/top");
}
