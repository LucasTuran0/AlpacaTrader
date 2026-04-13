const BASE = "/api";

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
