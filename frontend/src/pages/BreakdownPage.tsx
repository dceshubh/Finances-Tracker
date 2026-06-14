import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Profile, CategoryBreakdown, MerchantTransaction } from '../api/types';
import {
  ChevronDown, ChevronRight, TrendingUp, TrendingDown,
  ArrowUpRight, ArrowDownRight,
} from 'lucide-react';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function MerchantRow({ merchant, color, txType, filters }: {
  merchant: { description: string; total: number; count: number };
  color: 'emerald' | 'red';
  txType: string;
  filters: { profile_id?: number; year?: number; month?: number };
}) {
  const [expanded, setExpanded] = useState(false);
  const [transactions, setTransactions] = useState<MerchantTransaction[]>([]);
  const [loading, setLoading] = useState(false);

  const fmt = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  const loadTransactions = async () => {
    if (transactions.length > 0) {
      setExpanded(!expanded);
      return;
    }
    setLoading(true);
    const txns = await api.analytics.merchantTransactions({
      description: merchant.description,
      tx_type: txType,
      ...filters,
    });
    setTransactions(txns);
    setExpanded(true);
    setLoading(false);
  };

  return (
    <div>
      <div
        className="flex items-center justify-between px-5 py-2.5 pl-12 hover:bg-slate-100 cursor-pointer transition-colors border-b border-slate-100 last:border-b-0"
        onClick={loadTransactions}
      >
        <div className="flex items-center gap-2 min-w-0">
          {expanded ? (
            <ChevronDown size={12} className={`text-${color}-400 shrink-0`} />
          ) : (
            <ChevronRight size={12} className={`text-${color}-400 shrink-0`} />
          )}
          <span className="text-sm text-slate-700 truncate">{merchant.description}</span>
          <span className="text-xs text-slate-400 shrink-0">x{merchant.count}</span>
        </div>
        <span className={`text-sm font-medium text-${color}-600 shrink-0 ml-3`}>
          {fmt(merchant.total)}
        </span>
      </div>

      {/* Individual Transactions */}
      {expanded && (
        <div className="bg-white border-b border-slate-100">
          {loading ? (
            <div className="pl-16 pr-5 py-2 text-xs text-slate-400">Loading...</div>
          ) : (
            transactions.map(tx => (
              <div key={tx.id} className="flex items-center justify-between pl-16 pr-5 py-1.5 text-xs hover:bg-slate-50">
                <div className="flex items-center gap-4">
                  <span className="text-slate-400 w-20">{tx.date}</span>
                  <span className="text-slate-500">{tx.account_name}</span>
                </div>
                <span className={`font-medium ${color === 'emerald' ? 'text-emerald-600' : 'text-red-600'}`}>
                  {fmt(tx.amount)}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function BreakdownPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [incomeData, setIncomeData] = useState<CategoryBreakdown[]>([]);
  const [spendingData, setSpendingData] = useState<CategoryBreakdown[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedProfile, setSelectedProfile] = useState<number | undefined>();
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState<number | undefined>();

  const [expandedIncome, setExpandedIncome] = useState<Set<string>>(new Set());
  const [expandedSpending, setExpandedSpending] = useState<Set<string>>(new Set());

  const load = async () => {
    setLoading(true);
    const [p, inc, spend] = await Promise.all([
      api.profiles.list(),
      api.analytics.breakdown({ profile_id: selectedProfile, year: selectedYear, month: selectedMonth, tx_type: 'credit' }),
      api.analytics.breakdown({ profile_id: selectedProfile, year: selectedYear, month: selectedMonth, tx_type: 'debit' }),
    ]);
    setProfiles(p);
    setIncomeData(inc);
    setSpendingData(spend);
    setLoading(false);
  };

  useEffect(() => { load(); }, [selectedProfile, selectedYear, selectedMonth]);

  const fmt = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 });

  const totalIncome = incomeData.reduce((s, c) => s + c.total, 0);
  const totalSpending = spendingData.reduce((s, c) => s + c.total, 0);

  const toggleIncome = (cat: string) => {
    setExpandedIncome(prev => {
      const next = new Set(prev);
      next.has(cat) ? next.delete(cat) : next.add(cat);
      return next;
    });
  };

  const toggleSpending = (cat: string) => {
    setExpandedSpending(prev => {
      const next = new Set(prev);
      next.has(cat) ? next.delete(cat) : next.add(cat);
      return next;
    });
  };

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);
  const filters = { profile_id: selectedProfile, year: selectedYear, month: selectedMonth };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Breakdown</h2>
            <p className="text-slate-500 text-sm">Income & spending by category — click merchants to see individual transactions</p>
          </div>
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
        </div>
      </div>

      {/* Summary Cards */}
      {!loading && (
        <div className="grid grid-cols-3 gap-5 mb-8">
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
            <div className="text-sm text-emerald-600 font-medium">Total Income</div>
            <div className="text-2xl font-bold text-emerald-800">{fmt(totalIncome)}</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-xl p-5">
            <div className="text-sm text-red-600 font-medium">Total Spending</div>
            <div className="text-2xl font-bold text-red-800">{fmt(totalSpending)}</div>
          </div>
          <div className={`${totalIncome - totalSpending >= 0 ? 'bg-indigo-50 border-indigo-200' : 'bg-amber-50 border-amber-200'} border rounded-xl p-5`}>
            <div className={`text-sm font-medium ${totalIncome - totalSpending >= 0 ? 'text-indigo-600' : 'text-amber-600'}`}>Net Savings</div>
            <div className={`text-2xl font-bold ${totalIncome - totalSpending >= 0 ? 'text-indigo-800' : 'text-amber-800'}`}>
              {fmt(totalIncome - totalSpending)}
            </div>
            {totalIncome > 0 && (
              <div className="text-xs text-slate-500 mt-1">
                {((totalIncome - totalSpending) / totalIncome * 100).toFixed(1)}% savings rate
              </div>
            )}
          </div>
        </div>
      )}

      {loading ? (
        <div className="p-8 text-slate-500">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {/* Income Section */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                <TrendingUp size={20} className="text-emerald-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Income</h3>
                <p className="text-sm text-emerald-600 font-medium">{fmt(totalIncome)} across {incomeData.reduce((s, c) => s + c.count, 0)} transactions</p>
              </div>
            </div>

            <div className="space-y-2">
              {incomeData.length === 0 ? (
                <div className="text-slate-400 text-sm p-4">No income data for this period</div>
              ) : (
                incomeData.map(cat => (
                  <div key={cat.category} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <button
                      onClick={() => toggleIncome(cat.category)}
                      className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {expandedIncome.has(cat.category) ? (
                          <ChevronDown size={16} className="text-slate-400" />
                        ) : (
                          <ChevronRight size={16} className="text-slate-400" />
                        )}
                        <span className="font-medium text-slate-800 capitalize">{cat.category}</span>
                        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                          {cat.count} txns
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-400 rounded-full"
                            style={{ width: `${Math.min(100, (cat.total / totalIncome) * 100)}%` }}
                          />
                        </div>
                        <span className="text-sm font-semibold text-emerald-600 w-24 text-right">
                          {fmt(cat.total)}
                        </span>
                        <span className="text-xs text-slate-400 w-12 text-right">
                          {((cat.total / totalIncome) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </button>

                    {expandedIncome.has(cat.category) && (
                      <div className="border-t border-slate-100 bg-slate-50/50">
                        {cat.merchants.map((m, i) => (
                          <MerchantRow
                            key={i}
                            merchant={m}
                            color="emerald"
                            txType="credit"
                            filters={filters}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Spending Section */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                <TrendingDown size={20} className="text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Spending</h3>
                <p className="text-sm text-red-600 font-medium">{fmt(totalSpending)} across {spendingData.reduce((s, c) => s + c.count, 0)} transactions</p>
              </div>
            </div>

            <div className="space-y-2">
              {spendingData.length === 0 ? (
                <div className="text-slate-400 text-sm p-4">No spending data for this period</div>
              ) : (
                spendingData.map(cat => (
                  <div key={cat.category} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <button
                      onClick={() => toggleSpending(cat.category)}
                      className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {expandedSpending.has(cat.category) ? (
                          <ChevronDown size={16} className="text-slate-400" />
                        ) : (
                          <ChevronRight size={16} className="text-slate-400" />
                        )}
                        <span className="font-medium text-slate-800 capitalize">{cat.category}</span>
                        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                          {cat.count} txns
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-red-400 rounded-full"
                            style={{ width: `${Math.min(100, (cat.total / totalSpending) * 100)}%` }}
                          />
                        </div>
                        <span className="text-sm font-semibold text-red-600 w-24 text-right">
                          {fmt(cat.total)}
                        </span>
                        <span className="text-xs text-slate-400 w-12 text-right">
                          {((cat.total / totalSpending) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </button>

                    {expandedSpending.has(cat.category) && (
                      <div className="border-t border-slate-100 bg-slate-50/50">
                        {cat.merchants.map((m, i) => (
                          <MerchantRow
                            key={i}
                            merchant={m}
                            color="red"
                            txType="debit"
                            filters={filters}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
