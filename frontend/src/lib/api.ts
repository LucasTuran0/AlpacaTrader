const BASE = import.meta.env.VITE_BACKEND_URL ?? "/api";

export interface AccountInfo {
  equity: number;
  buying_power: number;
}

export interface Metrics {
  total_runs: number;
  current_equity: number;
  max_drawdown_pct: number;
  history: { date: string; equity: number }[];
}

export interface BanditArm {
  param_key: string;
  trials: number;
  total_reward: number;
  avg_reward: number;
}

export interface TradeHistoryItem {
  symbol: string;
  side: string;
  qty: number;
  entry_price: number | null;
  status: string;
  timestamp: string | null;
  run_id: string;
  params_used: Record<string, number> | null;
  reward: number | null;
}

export interface BotRunResult {
  run_id: string;
  status: string;
  reason?: string;
  params?: Record<string, number>;
  orders_count?: number;
}

export async function fetchAccount(): Promise<AccountInfo> {
  const res = await fetch(`${BASE}/account`);
  return res.json();
}

export async function fetchMetrics(): Promise<Metrics> {
  const res = await fetch(`${BASE}/bot/metrics`);
  return res.json();
}

export async function fetchBanditStats(): Promise<BanditArm[]> {
  const res = await fetch(`${BASE}/bot/bandit_stats`);
  return res.json();
}

export async function fetchTradeHistory(limit = 50): Promise<TradeHistoryItem[]> {
  const res = await fetch(`${BASE}/bot/trade_history?limit=${limit}`);
  return res.json();
}

export async function runBot(dryRun: boolean): Promise<BotRunResult> {
  const res = await fetch(`${BASE}/bot/run_once`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dry_run: dryRun }),
  });
  return res.json();
}

export async function triggerBacktest(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/bot/backtest`, { method: "POST" });
  return res.json();
}

export interface RiskStatus {
  vix: number | null;
  auto_regime: string;
  active_regime: string;
  override_active: boolean;
  trading_blocked: boolean;
  block_reason: string | null;
}

export async function fetchRiskStatus(): Promise<RiskStatus> {
  const res = await fetch(`${BASE}/bot/risk_status`);
  return res.json();
}

export async function setRiskOverride(mode: string | null): Promise<{ risk_override: string | null }> {
  const res = await fetch(`${BASE}/bot/risk_override`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function forceLiquidate(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/bot/force_liquidate`, { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
