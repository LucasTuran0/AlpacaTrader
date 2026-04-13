import { useEffect, useState } from "react";
import { Activity, DollarSign, TrendingDown } from "lucide-react";
import { fetchAccount, fetchMetrics, type AccountInfo, type Metrics } from "../lib/api";

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] px-5 py-4">
      <div className={`rounded-md p-2 ${color}`}>{icon}</div>
      <div>
        <p className="text-xs text-[var(--color-text-muted)]">{label}</p>
        <p className="text-lg font-semibold">{value}</p>
      </div>
    </div>
  );
}

export default function Header() {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    const load = () => {
      fetchAccount().then(setAccount).catch(() => {});
      fetchMetrics().then(setMetrics).catch(() => {});
    };
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const equity = account?.equity ?? 0;
  const buyingPower = account?.buying_power ?? 0;
  const drawdown = metrics?.max_drawdown_pct ?? 0;
  const totalRuns = metrics?.total_runs ?? 0;

  return (
    <header className="mb-6">
      <h1 className="mb-4 text-2xl font-bold tracking-tight">AlpacaTrader Dashboard</h1>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={<DollarSign size={18} />} label="Equity" value={`$${equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} color="bg-sky-500/20 text-sky-400" />
        <StatCard icon={<DollarSign size={18} />} label="Buying Power" value={`$${buyingPower.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} color="bg-emerald-500/20 text-emerald-400" />
        <StatCard icon={<TrendingDown size={18} />} label="Max Drawdown" value={`${drawdown.toFixed(2)}%`} color="bg-red-500/20 text-red-400" />
        <StatCard icon={<Activity size={18} />} label="Total Runs" value={totalRuns.toString()} color="bg-violet-500/20 text-violet-400" />
      </div>
    </header>
  );
}
