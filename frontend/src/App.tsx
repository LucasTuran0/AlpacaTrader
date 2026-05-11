import Header from "./components/Header";
import EquityChart from "./components/EquityChart";
import TradeHistory from "./components/TradeHistory";
import LogStream from "./components/LogStream";
import Controls from "./components/Controls";

export default function App() {
  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Header />
      <div className="grid gap-6 lg:grid-cols-2">
        <EquityChart />
        <Controls />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <TradeHistory />
        <LogStream />
      </div>
    </div>
  );
}
