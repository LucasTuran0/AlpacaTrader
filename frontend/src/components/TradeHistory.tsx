import { useEffect, useMemo, useState } from "react";
import { fetchTradeHistory, type TradeHistoryItem } from "../lib/api";

function formatTimestamp(ts: string | null): string {
  if (!ts) return "-";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

function formatPrice(price: number | null): string {
  if (price === null || Number.isNaN(price)) return "-";
  return `$${price.toFixed(2)}`;
}

function formatReward(reward: number | null): string {
  if (reward === null || Number.isNaN(reward)) return "-";
  const pct = reward * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

export default function TradeHistory() {
  const [trades, setTrades] = useState<TradeHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      try {
        const rows = await fetchTradeHistory(50);
        if (!mounted) return;
        setTrades(rows);
        setStale(false);
      } catch {
        if (!mounted) return;
        // Keep last successful data visible and just flag stale state.
        setStale(true);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    const id = setInterval(load, 3000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const hasTrades = trades.length > 0;

  const newestRunId = useMemo(() => (hasTrades ? trades[0].run_id : null), [hasTrades, trades]);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Trade History</h2>
        <div className="flex items-center gap-2">
          {stale && (
            <span className="rounded-full bg-amber-900/40 px-2.5 py-0.5 text-xs font-medium text-amber-300">
              Stale
            </span>
          )}
          {!stale && (
            <span className="rounded-full bg-emerald-900/40 px-2.5 py-0.5 text-xs font-medium text-emerald-300">
              Live (3s)
            </span>
          )}
        </div>
      </div>

      {loading && !hasTrades ? (
        <p className="py-8 text-center text-[var(--color-text-muted)]">Loading trade history...</p>
      ) : !hasTrades ? (
        <p className="py-8 text-center text-[var(--color-text-muted)]">No filled trades yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Time
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Symbol
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Side
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Qty
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Price
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Reward
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, idx) => {
                const liquidationLike = trade.side.toLowerCase() === "sell";
                return (
                  <tr
                    key={`${trade.run_id}-${trade.symbol}-${trade.timestamp ?? idx}`}
                    className="border-b border-[var(--color-border)]/50 hover:bg-white/5"
                    title={`Run: ${trade.run_id}`}
                  >
                    <td className="px-3 py-2 font-mono text-xs">{formatTimestamp(trade.timestamp)}</td>
                    <td className="px-3 py-2 font-semibold">{trade.symbol}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          trade.side.toLowerCase() === "buy"
                            ? "bg-emerald-900/40 text-emerald-300"
                            : "bg-rose-900/40 text-rose-300"
                        }`}
                      >
                        {trade.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-3 py-2">{trade.qty}</td>
                    <td className="px-3 py-2">{formatPrice(trade.entry_price)}</td>
                    <td
                      className={`px-3 py-2 font-semibold ${
                        (trade.reward ?? 0) >= 0 ? "text-[var(--color-green)]" : "text-[var(--color-red)]"
                      }`}
                    >
                      {formatReward(trade.reward)}
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-[var(--color-text-muted)]">
                        {liquidationLike ? `${trade.status} (exit/liquidate)` : trade.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {newestRunId && (
            <p className="mt-3 text-xs text-[var(--color-text-muted)]">
              Most recent run: <span className="font-mono">{newestRunId}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
