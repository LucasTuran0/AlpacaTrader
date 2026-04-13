import { useState } from "react";
import { Play, FlaskConical, Zap } from "lucide-react";
import { runBot, triggerBacktest } from "../lib/api";

export default function Controls() {
  const [loading, setLoading] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string>("");

  const handle = async (action: string, fn: () => Promise<unknown>) => {
    setLoading(action);
    setLastResult("");
    try {
      const result = await fn();
      setLastResult(`${action}: ${JSON.stringify(result)}`);
    } catch (e) {
      setLastResult(`${action} failed: ${e}`);
    } finally {
      setLoading(null);
    }
  };

  const btn = "flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50";

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
      <h2 className="mb-4 text-lg font-semibold">Controls</h2>
      <div className="flex flex-wrap gap-3">
        <button className={`${btn} bg-sky-600 hover:bg-sky-500`} disabled={loading !== null} onClick={() => handle("Dry Run", () => runBot(true))}>
          <Play size={16} /> Dry Run
        </button>
        <button className={`${btn} bg-emerald-600 hover:bg-emerald-500`} disabled={loading !== null} onClick={() => handle("Live Run", () => runBot(false))}>
          <Zap size={16} /> Live Run
        </button>
        <button className={`${btn} bg-violet-600 hover:bg-violet-500`} disabled={loading !== null} onClick={() => handle("Backtest", () => triggerBacktest())}>
          <FlaskConical size={16} /> Run Backtest
        </button>
      </div>
      {loading && <p className="mt-3 text-xs text-[var(--color-text-muted)]">Running {loading}...</p>}
      {lastResult && <p className="mt-3 rounded bg-[var(--color-bg-primary)] p-2 font-mono text-xs">{lastResult}</p>}
    </div>
  );
}
