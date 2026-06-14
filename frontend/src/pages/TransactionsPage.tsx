import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Transaction, Account, Profile } from '../api/types';
import {
  Search, ArrowUpRight, ArrowDownRight, Trash2, Pencil, Check, X,
  ChevronLeft, ChevronRight, AlertTriangle, ArrowUp, ArrowDown, ArrowUpDown,
} from 'lucide-react';

const CATEGORIES = [
  'all', 'groceries', 'dining', 'gas', 'transportation', 'auto', 'utilities', 'rent',
  'insurance', 'healthcare', 'shopping', 'subscriptions', 'travel', 'education',
  'entertainment', 'investments', 'transfer', 'income', 'fees', 'other', 'uncategorized',
];

const PAGE_SIZE = 50;

type SortField = 'date' | 'amount' | 'description' | 'category';
type SortDir = 'asc' | 'desc';

export default function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  // Sorting
  const [sortBy, setSortBy] = useState<SortField>('date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // Filters — initialize from URL params
  const [filterProfile, setFilterProfile] = useState<number | undefined>();
  const [filterAccount, setFilterAccount] = useState<number | undefined>();
  const [filterCategory, setFilterCategory] = useState<string>(() => {
    const cat = searchParams.get('category');
    return cat && CATEGORIES.includes(cat) ? cat : 'all';
  });
  const [filterType, setFilterType] = useState<string>(() => {
    const t = searchParams.get('type');
    return t === 'credit' || t === 'debit' ? t : 'all';
  });
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{
    description: string; amount: string; category: string; tx_type: string; date: string;
  }>({ description: '', amount: '', category: '', tx_type: '', date: '' });

  // Clear-all modal
  const [showClearModal, setShowClearModal] = useState(false);

  const filterParams = {
    profile_id: filterProfile,
    account_id: filterAccount,
    category: filterCategory !== 'all' ? filterCategory : undefined,
    tx_type: filterType !== 'all' ? filterType : undefined,
    date_from: filterDateFrom || undefined,
    date_to: filterDateTo || undefined,
  };

  const load = async () => {
    setLoading(true);
    const [tx, countRes, a, p] = await Promise.all([
      api.transactions.list({ ...filterParams, sort_by: sortBy, sort_dir: sortDir, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
      api.transactions.count(filterParams),
      api.accounts.list(),
      api.profiles.list(),
    ]);
    setTransactions(tx);
    setTotalCount(countRes.count);
    setAccounts(a);
    setProfiles(p);
    setLoading(false);
  };

  // Sync category filter back to URL params
  useEffect(() => {
    const newParams = new URLSearchParams(searchParams);
    if (filterCategory !== 'all') {
      newParams.set('category', filterCategory);
    } else {
      newParams.delete('category');
    }
    if (filterType !== 'all') {
      newParams.set('type', filterType);
    } else {
      newParams.delete('type');
    }
    setSearchParams(newParams, { replace: true });
  }, [filterCategory, filterType]);

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDir(field === 'amount' ? 'desc' : 'asc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) return <ArrowUpDown size={12} className="text-slate-300" />;
    return sortDir === 'asc'
      ? <ArrowUp size={12} className="text-indigo-600" />
      : <ArrowDown size={12} className="text-indigo-600" />;
  };

  useEffect(() => { setPage(0); }, [filterProfile, filterAccount, filterCategory, filterType, filterDateFrom, filterDateTo, sortBy, sortDir]);
  useEffect(() => { load(); }, [filterProfile, filterAccount, filterCategory, filterType, filterDateFrom, filterDateTo, sortBy, sortDir, page]);

  const getAccountName = (id: number) => accounts.find(a => a.id === id)?.account_name ?? 'Unknown';
  const fmt = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  const filtered = searchTerm
    ? transactions.filter(t => t.description.toLowerCase().includes(searchTerm.toLowerCase()))
    : transactions;

  const totalIncome = filtered.filter(t => t.tx_type === 'credit').reduce((s, t) => s + t.amount, 0);
  const totalSpending = filtered.filter(t => t.tx_type === 'debit').reduce((s, t) => s + t.amount, 0);
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  // Edit handlers
  const startEdit = (tx: Transaction) => {
    setEditingId(tx.id);
    setEditForm({
      description: tx.description,
      amount: String(tx.amount),
      category: tx.category,
      tx_type: tx.tx_type,
      date: tx.date,
    });
  };

  const cancelEdit = () => { setEditingId(null); };

  const saveEdit = async () => {
    if (editingId === null) return;
    await api.transactions.update(editingId, {
      description: editForm.description,
      amount: parseFloat(editForm.amount),
      category: editForm.category,
      tx_type: editForm.tx_type,
      date: editForm.date,
    });
    setEditingId(null);
    load();
  };

  const deleteTx = async (id: number) => {
    await api.transactions.delete(id);
    load();
  };

  const clearAll = async () => {
    await api.transactions.deleteAll(
      filterProfile ? { profile_id: filterProfile } : filterAccount ? { account_id: filterAccount } : undefined
    );
    setShowClearModal(false);
    load();
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Transactions</h2>
          <p className="text-slate-500 text-sm">{totalCount} total transactions (page {page + 1} of {totalPages || 1})</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-4 text-sm">
            <span className="text-emerald-600 font-medium">Income: {fmt(totalIncome)}</span>
            <span className="text-red-600 font-medium">Spending: {fmt(totalSpending)}</span>
            <span className={`font-semibold ${totalIncome - totalSpending >= 0 ? 'text-indigo-600' : 'text-amber-600'}`}>
              Net: {fmt(totalIncome - totalSpending)}
            </span>
          </div>
          <button
            onClick={() => setShowClearModal(true)}
            className="px-3 py-2 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors flex items-center gap-1.5"
          >
            <Trash2 size={14} /> Clear All
          </button>
        </div>
      </div>

      {/* Clear All Confirmation Modal */}
      {showClearModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle size={20} className="text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900">Clear All Transactions?</h3>
            </div>
            <p className="text-slate-600 text-sm mb-6">
              This will permanently delete {filterProfile ? 'all transactions for the selected profile' : 'ALL transactions across all accounts'}.
              This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowClearModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={clearAll}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                Yes, Delete All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search transactions..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <select value={filterProfile ?? ''} onChange={e => setFilterProfile(e.target.value ? Number(e.target.value) : undefined)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">All Profiles</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select value={filterAccount ?? ''} onChange={e => setFilterAccount(e.target.value ? Number(e.target.value) : undefined)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">All Accounts</option>
            {accounts.map(a => <option key={a.id} value={a.id}>{a.account_name}</option>)}
          </select>
          <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            {CATEGORIES.map(c => <option key={c} value={c}>{c === 'all' ? 'All Categories' : c}</option>)}
          </select>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="all">All Types</option>
            <option value="credit">Income</option>
            <option value="debit">Spending</option>
          </select>
          <input type="date" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          <input type="date" value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
      </div>

      {/* Category Analytics Bar */}
      {filterCategory !== 'all' && totalCount > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-indigo-900 capitalize">{filterCategory}</span>
              <span className="text-xs text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">{totalCount} transactions</span>
            </div>
            <div className="flex items-center gap-6 text-sm">
              <div>
                <span className="text-indigo-500">Total: </span>
                <span className="font-semibold text-indigo-900">{fmt(totalSpending + totalIncome)}</span>
              </div>
              <div>
                <span className="text-indigo-500">Page avg: </span>
                <span className="font-semibold text-indigo-900">
                  {fmt((totalSpending + totalIncome) / (filtered.length || 1))}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400">No transactions found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-slate-500">
                  <button onClick={() => toggleSort('date')} className="inline-flex items-center gap-1 hover:text-indigo-600 transition-colors">
                    Date <SortIcon field="date" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 font-medium text-slate-500">
                  <button onClick={() => toggleSort('description')} className="inline-flex items-center gap-1 hover:text-indigo-600 transition-colors">
                    Description <SortIcon field="description" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 font-medium text-slate-500">Account</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500">
                  <button onClick={() => toggleSort('category')} className="inline-flex items-center gap-1 hover:text-indigo-600 transition-colors">
                    Category <SortIcon field="category" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 font-medium text-slate-500">Type</th>
                <th className="text-right px-4 py-3 font-medium text-slate-500">
                  <button onClick={() => toggleSort('amount')} className="inline-flex items-center gap-1 hover:text-indigo-600 transition-colors ml-auto">
                    Amount <SortIcon field="amount" />
                  </button>
                </th>
                <th className="text-center px-4 py-3 font-medium text-slate-500 w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(tx => (
                <tr key={tx.id} className="hover:bg-slate-50 transition-colors">
                  {editingId === tx.id ? (
                    /* ---- EDIT MODE ---- */
                    <>
                      <td className="px-4 py-2">
                        <input
                          type="date"
                          value={editForm.date}
                          onChange={e => setEditForm(f => ({ ...f, date: e.target.value }))}
                          className="w-full px-2 py-1 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="text"
                          value={editForm.description}
                          onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                          className="w-full px-2 py-1 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      </td>
                      <td className="px-4 py-2 text-slate-500 text-xs">{getAccountName(tx.account_id)}</td>
                      <td className="px-4 py-2">
                        <select
                          value={editForm.category}
                          onChange={e => setEditForm(f => ({ ...f, category: e.target.value }))}
                          className="w-full px-2 py-1 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        >
                          {CATEGORIES.filter(c => c !== 'all').map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </td>
                      <td className="px-4 py-2">
                        <select
                          value={editForm.tx_type}
                          onChange={e => setEditForm(f => ({ ...f, tx_type: e.target.value }))}
                          className="w-full px-2 py-1 border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        >
                          <option value="credit">Income</option>
                          <option value="debit">Expense</option>
                        </select>
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="number"
                          step="0.01"
                          value={editForm.amount}
                          onChange={e => setEditForm(f => ({ ...f, amount: e.target.value }))}
                          className="w-full px-2 py-1 border border-slate-300 rounded text-xs text-right focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={saveEdit} className="p-1 text-emerald-600 hover:bg-emerald-50 rounded" title="Save">
                            <Check size={16} />
                          </button>
                          <button onClick={cancelEdit} className="p-1 text-slate-400 hover:bg-slate-100 rounded" title="Cancel">
                            <X size={16} />
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    /* ---- VIEW MODE ---- */
                    <>
                      <td className="px-4 py-3 text-slate-600 whitespace-nowrap">{tx.date}</td>
                      <td className="px-4 py-3 text-slate-800 max-w-sm truncate">{tx.description}</td>
                      <td className="px-4 py-3 text-slate-500">{getAccountName(tx.account_id)}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 capitalize">{tx.category}</span>
                      </td>
                      <td className="px-4 py-3">
                        {tx.tx_type === 'credit' ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-600"><ArrowUpRight size={12} />Income</span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-red-600"><ArrowDownRight size={12} />Expense</span>
                        )}
                      </td>
                      <td className={`px-4 py-3 text-right font-medium whitespace-nowrap ${tx.tx_type === 'credit' ? 'text-emerald-600' : 'text-red-600'}`}>
                        {tx.tx_type === 'credit' ? '+' : '-'}{fmt(tx.amount)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => startEdit(tx)} className="p-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors" title="Edit">
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => deleteTx(tx.id)} className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50">
            <p className="text-sm text-slate-500">
              Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, totalCount)} of {totalCount}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg border border-slate-300 text-slate-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 7) {
                  pageNum = i;
                } else if (page < 3) {
                  pageNum = i;
                } else if (page > totalPages - 4) {
                  pageNum = totalPages - 7 + i;
                } else {
                  pageNum = page - 3 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${
                      page === pageNum
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-600 hover:bg-white border border-slate-300'
                    }`}
                  >
                    {pageNum + 1}
                  </button>
                );
              })}
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg border border-slate-300 text-slate-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
