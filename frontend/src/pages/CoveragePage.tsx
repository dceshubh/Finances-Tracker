import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { CoverageData } from '../api/types';
import { CheckCircle2, XCircle, AlertTriangle, Info } from 'lucide-react';

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function formatMonth(ym: string) {
  const [y, m] = ym.split('-').map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

export default function CoveragePage() {
  const [data, setData] = useState<CoverageData | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    // Extend 1 month past the latest statement so upcoming statements show as "missing"
    api.statements.coverage(1).then(d => {
      setData(d);
      setLoading(false);
    });
  }, []);

  const goToStatement = (statementId?: number) => {
    if (statementId) navigate('/upload');
  };

  if (loading) return <div className="p-8 text-slate-500">Loading...</div>;

  if (!data || data.months.length === 0) {
    return (
      <div className="p-6">
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Statement Coverage</h2>
        <p className="text-slate-500">No statements uploaded yet. Upload some statements to see coverage.</p>
      </div>
    );
  }

  // Count totals for the summary
  let totalCells = 0, uploadedCells = 0, missingCells = 0, warningCells = 0;
  for (const p of data.profiles) {
    for (const a of p.accounts) {
      if (a.note) continue; // skip accounts bundled into other statements
      for (const ym of data.months) {
        const cell = a.coverage[ym];
        totalCells++;
        if (cell.status === 'uploaded') uploadedCells++;
        else if (cell.status === 'warning') warningCells++;
        else missingCells++;
      }
    }
  }

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-slate-900 mb-1">Statement Coverage</h2>
      <p className="text-slate-500 mb-6">
        Which months have been uploaded for each account, across {data.months[0] ? formatMonth(data.months[0]) : ''} – {data.months[data.months.length - 1] ? formatMonth(data.months[data.months.length - 1]) : ''}.
      </p>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6 max-w-xl">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="flex items-center gap-2 text-green-600 mb-1">
            <CheckCircle2 size={16} />
            <span className="text-xs font-semibold uppercase tracking-wider">Uploaded</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{uploadedCells}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="flex items-center gap-2 text-amber-600 mb-1">
            <AlertTriangle size={16} />
            <span className="text-xs font-semibold uppercase tracking-wider">Warnings</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{warningCells}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="flex items-center gap-2 text-red-500 mb-1">
            <XCircle size={16} />
            <span className="text-xs font-semibold uppercase tracking-wider">Missing</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{missingCells}</div>
        </div>
      </div>

      {/* One table per profile */}
      <div className="space-y-8">
        {data.profiles.map(profile => (
          <section key={profile.profile_id}>
            <h3 className="text-lg font-semibold text-slate-800 mb-3">{profile.profile_name}</h3>
            <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left px-4 py-3 font-semibold text-slate-600 sticky left-0 bg-white">Account</th>
                    {data.months.map(ym => (
                      <th key={ym} className="text-center px-3 py-3 font-semibold text-slate-600 whitespace-nowrap">
                        {formatMonth(ym)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {profile.accounts.map(account => (
                    <tr key={account.account_id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                      <td className="px-4 py-3 sticky left-0 bg-white">
                        <div className="font-medium text-slate-800">{account.account_name}</div>
                        <div className="text-xs text-slate-400">
                          {account.institution.replace('_', ' ')} &middot; {account.account_type.replace('_', ' ')}
                          {account.last_four && ` · ****${account.last_four}`}
                        </div>
                        {account.note && (
                          <div className="text-xs text-blue-500 flex items-center gap-1 mt-0.5">
                            <Info size={12} /> {account.note}
                          </div>
                        )}
                      </td>
                      {data.months.map(ym => {
                        const cell = account.coverage[ym];
                        if (account.note) {
                          return (
                            <td key={ym} className="text-center px-3 py-3">
                              <span className="text-slate-300">—</span>
                            </td>
                          );
                        }
                        return (
                          <td key={ym} className="text-center px-3 py-3">
                            {cell.status === 'uploaded' && (
                              <button
                                title={cell.filename}
                                onClick={() => goToStatement(cell.statement_id)}
                                className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-green-100 text-green-600 hover:bg-green-200 transition-colors"
                              >
                                <CheckCircle2 size={16} />
                              </button>
                            )}
                            {cell.status === 'warning' && (
                              <button
                                title={cell.filename}
                                onClick={() => goToStatement(cell.statement_id)}
                                className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-100 text-amber-600 hover:bg-amber-200 transition-colors"
                              >
                                <AlertTriangle size={16} />
                              </button>
                            )}
                            {cell.status === 'missing' && (
                              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-red-50 text-red-300">
                                <XCircle size={16} />
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-6 text-xs text-slate-500">
        <span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-green-600" /> Uploaded & validated</span>
        <span className="flex items-center gap-1.5"><AlertTriangle size={14} className="text-amber-600" /> Uploaded with validation warning</span>
        <span className="flex items-center gap-1.5"><XCircle size={14} className="text-red-300" /> Not uploaded yet</span>
      </div>
    </div>
  );
}
