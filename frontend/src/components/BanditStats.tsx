import { useEffect, useState } from "react";
import { fetchBanditStats, type BanditArm } from "../lib/api";

export default function BanditStats() {
  const [arms, setArms] = useState<BanditArm[]>([]);
  const [sortKey, setSortKey] = useState<keyof BanditArm>("avg_reward");
  const [asc, setAsc] = useState(false);

  useEffect(() => {
    const load = () => {
      fetchBanditStats().then(setArms).catch(() => {});
    };
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  const toggleSort = (key: keyof BanditArm) => {
    if (sortKey === key) setAsc(!asc);
    else {
      setSortKey(key);
      setAsc(false);
    }
  };

  const sorted = [...arms].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    return asc ? (av > bv ? 1 : -1) : av < bv ? 1 : -1;
  });

  const th = (label: string, key: keyof BanditArm) => (
    <th className="cursor-pointer px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)] hover:text-[var(--color-text)]" onClick={() => toggleSort(key)}>
      {label} {sortKey === key ? (asc ? "▲" : "▼") : ""}
    </th>
  );

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
      <h2 className="mb-4 text-lg font-semibold">Bandit Strategy Arms</h2>
      {arms.length === 0 ? (
        <p className="py-8 text-center text-[var(--color-text-muted)]">No bandit data yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                {th("Parameters", "param_key")}
                {th("Trials", "trials")}
                {th("Total Reward", "total_reward")}
                {th("Avg Reward", "avg_reward")}
              </tr>
            </thead>
            <tbody>
              {sorted.slice(0, 20).map((arm) => (
                <tr key={arm.param_key} className="border-b border-[var(--color-border)]/50 hover:bg-white/5">
                  <td className="px-4 py-2 font-mono text-xs">{arm.param_key}</td>
                  <td className="px-4 py-2">{arm.trials}</td>
                  <td className="px-4 py-2">{arm.total_reward.toFixed(2)}</td>
                  <td className={`px-4 py-2 font-semibold ${arm.avg_reward >= 0 ? "text-[var(--color-green)]" : "text-[var(--color-red)]"}`}>
                    {arm.avg_reward.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
