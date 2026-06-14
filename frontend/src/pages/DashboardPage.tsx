import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Profile, DashboardData, TimePeriodData } from '../api/types';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart,
} from 'recharts';
import { TrendingUp, TrendingDown, Wallet, ArrowUpRight, ArrowDownRight, ArrowLeftRight, Download } from 'lucide-react';

const COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#eab308',
  '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6', '#a855f7', '#64748b',
];

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function StatCard({ title, value, icon: Icon, color, subtext }: {
  title: string; value: string; icon: any; color: string; subtext?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-500">{title}</span>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={20} className="text-white" />
        </div>
      </div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      {subtext && <div className="text-xs text-slate-400 mt-1">{subtext}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [data, setData] = useState<DashboardData | null>(null);
  const [weeklyData, setWeeklyData] = useState<TimePeriodData[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<number | undefined>();
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState<number | undefined>();
  const [viewMode, setViewMode] = useState<'monthly' | 'weekly' | 'yearly'>('monthly');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [p, d] = await Promise.all([
      api.profiles.list(),
      api.analytics.dashboard({ profile_id: selectedProfile, year: selectedYear, month: selectedMonth }),
    ]);
    setProfiles(p);
    setData(d);

    if (viewMode === 'weekly') {
      const w = await api.analytics.weekly({ profile_id: selectedProfile, year: selectedYear });
      setWeeklyData(w);
    }

    setLoading(false);
  };

  useEffect(() => { load(); }, [selectedProfile, selectedYear, selectedMonth, viewMode]);

  const fmt = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 });

  if (loading && !data) return <div className="p-8 text-slate-500">Loading...</div>;
  if (!data) return <div className="p-8 text-slate-500">No data available. Upload some statements first.</div>;

  const years = [...new Set(data.monthly_trend.map(t => parseInt(t.month.split('-')[0])))].sort();
  if (years.length === 0) years.push(new Date().getFullYear());

  const monthlyChartData = data.monthly_trend.map(t => ({
    month: MONTHS[parseInt(t.month.split('-')[1]) - 1] || t.month,
    Income: t.income,
    Spending: t.spending,
    Savings: t.income - t.spending,
  }));

  return (
    <div className="p-8">
      <div className="mb-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Dashboard</h2>
            <p className="text-slate-500 text-sm">Your financial overview</p>
          </div>
          <button
            onClick={() => {
              const params = new URLSearchParams();
              if (selectedProfile) params.set('profile_id', String(selectedProfile));
              if (selectedYear) params.set('year', String(selectedYear));
              if (selectedMonth) params.set('month', String(selectedMonth));
              const qs = params.toString();
              window.open(`/api/export/excel${qs ? `?${qs}` : ''}`, '_blank');
            }}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors flex items-center gap-2"
          >
            <Download size={16} /> Export
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedProfile ?? ''}
            onChange={e => setSelectedProfile(e.target.value ? Number(e.target.value) : undefined)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Profiles</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select
            value={selectedYear}
            onChange={e => setSelectedYear(Number(e.target.value))}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <select
            value={selectedMonth ?? ''}
            onChange={e => setSelectedMonth(e.target.value ? Number(e.target.value) : undefined)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Months</option>
            {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
          </select>
          <div className="flex bg-slate-100 rounded-lg p-0.5">
            {(['monthly', 'weekly', 'yearly'] as const).map(mode => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  viewMode === mode ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
        <StatCard
          title="Total Income"
          value={fmt(data.total_income)}
          icon={ArrowUpRight}
          color="bg-emerald-500"
          subtext="Excludes transfers"
        />
        <StatCard
          title="Total Spending"
          value={fmt(data.total_spending)}
          icon={ArrowDownRight}
          color="bg-red-500"
          subtext="Excludes transfers"
        />
        <StatCard
          title="Net Savings"
          value={fmt(data.net_savings)}
          icon={Wallet}
          color={data.net_savings >= 0 ? 'bg-indigo-500' : 'bg-amber-500'}
          subtext={data.total_income > 0 ? `${((data.net_savings / data.total_income) * 100).toFixed(1)}% savings rate` : undefined}
        />
        <StatCard
          title="Internal Transfers"
          value={fmt(data.total_transfers || 0)}
          icon={ArrowLeftRight}
          color="bg-slate-500"
          subtext="Between your accounts"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        {/* Trend Chart */}
        <div className="col-span-2 bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">
            {viewMode === 'monthly' ? 'Monthly' : viewMode === 'weekly' ? 'Weekly' : 'Yearly'} Trend
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={viewMode === 'weekly' ? weeklyData.map(w => ({
              period: w.week || w.date || Object.values(w).find(v => typeof v === 'string'),
              Income: w.income,
              Spending: w.spending,
            })) : monthlyChartData}>
              <defs>
                <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey={viewMode === 'weekly' ? 'period' : 'month'} tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '13px' }}
                formatter={(v: number) => fmt(v)}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Area type="monotone" dataKey="Income" stroke="#22c55e" fill="url(#incomeGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="Spending" stroke="#ef4444" fill="url(#spendGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Category Pie */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">Spending by Category</h3>
          {data.category_breakdown.length === 0 ? (
            <div className="h-[300px] flex items-center justify-center text-slate-400 text-sm">No spending data</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={data.category_breakdown}
                    dataKey="total"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={45}
                    className="cursor-pointer"
                    onClick={(entry) => {
                      if (entry?.category) navigate(`/transactions?category=${entry.category}`);
                    }}
                  >
                    {data.category_breakdown.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ borderRadius: '8px', fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-2 space-y-1.5 max-h-[120px] overflow-y-auto">
                {data.category_breakdown.slice(0, 8).map((c, i) => (
                  <div
                    key={c.category}
                    className="flex items-center justify-between text-xs cursor-pointer hover:bg-slate-50 rounded px-1 py-0.5 -mx-1 transition-colors"
                    onClick={() => navigate(`/transactions?category=${c.category}`)}
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="text-slate-600 capitalize">{c.category}</span>
                    </div>
                    <span className="font-medium text-slate-800">{fmt(c.total)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Account Breakdown */}
      {data.account_breakdown.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">By Account</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.account_breakdown.map(a => ({
              name: a.account_name,
              Income: a.income,
              Spending: a.spending,
            }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ borderRadius: '8px', fontSize: '13px' }} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="Income" fill="#22c55e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Spending" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent Transactions */}
      {data.recent_transactions.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="text-sm font-semibold text-slate-800">Recent Transactions</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-6 py-3 font-medium text-slate-500">Date</th>
                <th className="text-left px-6 py-3 font-medium text-slate-500">Description</th>
                <th className="text-left px-6 py-3 font-medium text-slate-500">Account</th>
                <th className="text-left px-6 py-3 font-medium text-slate-500">Category</th>
                <th className="text-right px-6 py-3 font-medium text-slate-500">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.recent_transactions.slice(0, 20).map(tx => (
                <tr key={tx.id} className="hover:bg-slate-50">
                  <td className="px-6 py-3 text-slate-600">{tx.date}</td>
                  <td className="px-6 py-3 text-slate-800 max-w-xs truncate">{tx.description}</td>
                  <td className="px-6 py-3 text-slate-500">{tx.account_name}</td>
                  <td className="px-6 py-3">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 capitalize">{tx.category}</span>
                  </td>
                  <td className={`px-6 py-3 text-right font-medium ${tx.tx_type === 'credit' ? 'text-emerald-600' : 'text-red-600'}`}>
                    {tx.tx_type === 'credit' ? '+' : '-'}{fmt(tx.amount)}
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
