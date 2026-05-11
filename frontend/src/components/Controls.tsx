import { useEffect, useState } from "react";
import { Play, FlaskConical, Zap, OctagonX, ShieldOff, ShieldCheck } from "lucide-react";
import {
  runBot,
  triggerBacktest,
  fetchRiskStatus,
  setRiskOverride,
  forceLiquidate,
} from "../lib/api";

export default function Controls() {
  const [loading, setLoading] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string>("");
  const [halted, setHalted] = useState<boolean>(false);
  const [activeRegime, setActiveRegime] = useState<string>("");

  const refreshRisk = async () => {
    try {
      const s = await fetchRiskStatus();
      setHalted(s.override_active && s.active_regime === "CRISIS");
      setActiveRegime(s.active_regime);
    } catch {
      // ignore — backend may be momentarily unavailable
    }
  };

  useEffect(() => {
    refreshRisk();
    const id = setInterval(refreshRisk, 5000);
    return () => clearInterval(id);
  }, []);

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

  const handleToggleHalt = async () => {
    const next = halted ? null : "CRISIS";
    await handle(halted ? "Resume Trading" : "Halt Trading", () => setRiskOverride(next));
    refreshRisk();
  };

  const handleLiquidate = async () => {
    const ok = window.confirm(
      "Close ALL open positions immediately?\n\nThis cannot be undone — every position will be market-sold at the current price."
    );
    if (!ok) return;
    await handle("Force Liquidate", () => forceLiquidate());
  };

  const btn =
    "flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50";

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Controls</h2>
        {activeRegime && (
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              halted
                ? "bg-rose-900/40 text-rose-300"
                : activeRegime === "SHIELD_ACTIVE"
                ? "bg-amber-900/40 text-amber-300"
                : "bg-emerald-900/40 text-emerald-300"
            }`}
          >
            {halted ? "HALTED" : activeRegime}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-3">
        <button
          className={`${btn} bg-sky-600 hover:bg-sky-500`}
          disabled={loading !== null}
          onClick={() => handle("Dry Run", () => runBot(true))}
        >
          <Play size={16} /> Dry Run
        </button>
        <button
          className={`${btn} bg-emerald-600 hover:bg-emerald-500`}
          disabled={loading !== null || halted}
          onClick={() => handle("Live Run", () => runBot(false))}
          title={halted ? "Resume trading first to enable live runs" : ""}
        >
          <Zap size={16} /> Live Run
        </button>
        <button
          className={`${btn} bg-violet-600 hover:bg-violet-500`}
          disabled={loading !== null}
          onClick={() => handle("Backtest", () => triggerBacktest())}
        >
          <FlaskConical size={16} /> Run Backtest
        </button>
        <button
          className={`${btn} ${
            halted
              ? "bg-emerald-700 hover:bg-emerald-600"
              : "bg-amber-600 hover:bg-amber-500"
          }`}
          disabled={loading !== null}
          onClick={handleToggleHalt}
          title={
            halted
              ? "Clear risk override and resume normal trading"
              : "Force CRISIS regime — blocks all new entries (existing positions stay open)"
          }
        >
          {halted ? <ShieldCheck size={16} /> : <ShieldOff size={16} />}
          {halted ? "Resume Trading" : "Halt Trading"}
        </button>
        <button
          className={`${btn} bg-rose-700 hover:bg-rose-600`}
          disabled={loading !== null}
          onClick={handleLiquidate}
          title="Close all open positions immediately (irreversible)"
        >
          <OctagonX size={16} /> Close All Positions
        </button>
      </div>
      {loading && (
        <p className="mt-3 text-xs text-[var(--color-text-muted)]">Running {loading}...</p>
      )}
      {lastResult && (
        <p className="mt-3 rounded bg-[var(--color-bg-primary)] p-2 font-mono text-xs">
          {lastResult}
        </p>
      )}
    </div>
  );
}
