import { useEffect, useRef } from "react";
import { Wifi, WifiOff } from "lucide-react";
import { useWebSocket } from "../hooks/useWebSocket";

export default function LogStream() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const backendHost = import.meta.env.VITE_WS_URL ?? `${proto}//${window.location.host}`;
  const wsUrl = `${backendHost}/ws/logs`;
  const { messages, connected } = useWebSocket(wsUrl);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Live Logs</h2>
        <span className={`flex items-center gap-1.5 text-xs ${connected ? "text-[var(--color-green)]" : "text-[var(--color-red)]"}`}>
          {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
      <div className="h-64 overflow-y-auto rounded bg-[var(--color-bg-primary)] p-3 font-mono text-xs leading-relaxed">
        {messages.length === 0 && <p className="text-[var(--color-text-muted)]">Waiting for log events...</p>}
        {messages.map((msg, i) => (
          <div key={i} className="border-b border-[var(--color-border)]/30 py-0.5">
            {msg}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
