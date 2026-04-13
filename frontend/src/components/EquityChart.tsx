import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { fetchMetrics } from "../lib/api";

interface Point {
  date: string;
  equity: number;
}

export default function EquityChart() {
  const [data, setData] = useState<Point[]>([]);

  useEffect(() => {
    const load = () => {
      fetchMetrics()
        .then((m) => setData(m.history ?? []))
        .catch(() => {});
    };
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
      <h2 className="mb-4 text-lg font-semibold">Equity Curve</h2>
      {data.length === 0 ? (
        <p className="py-12 text-center text-[var(--color-text-muted)]">No equity data yet. Run the bot or a backtest to generate data.</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
              labelStyle={{ color: "#94a3b8" }}
              formatter={(value) => [`$${Number(value).toLocaleString()}`, "Equity"]}
            />
            <Line type="monotone" dataKey="equity" stroke="#38bdf8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
