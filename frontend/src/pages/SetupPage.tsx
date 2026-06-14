import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Profile, Account } from '../api/types';
import { INSTITUTIONS, ACCOUNT_TYPES } from '../api/types';
import { UserPlus, Plus, Trash2, CreditCard, Building2 } from 'lucide-react';

export default function SetupPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [newProfile, setNewProfile] = useState({ name: '', role: 'self' });
  const [newAccount, setNewAccount] = useState({
    profile_id: 0, institution: 'chase', account_type: 'checking', account_name: '', last_four: '',
  });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [p, a] = await Promise.all([api.profiles.list(), api.accounts.list()]);
    setProfiles(p);
    setAccounts(a);
    if (p.length > 0 && newAccount.profile_id === 0) {
      setNewAccount(prev => ({ ...prev, profile_id: p[0].id }));
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const addProfile = async () => {
    if (!newProfile.name.trim()) return;
    await api.profiles.create(newProfile);
    setNewProfile({ name: '', role: 'self' });
    load();
  };

  const addAccount = async () => {
    if (!newAccount.account_name.trim() || !newAccount.profile_id) return;
    await api.accounts.create(newAccount);
    setNewAccount(prev => ({ ...prev, account_name: '', last_four: '' }));
    load();
  };

  const deleteProfile = async (id: number) => {
    await api.profiles.delete(id);
    load();
  };

  const deleteAccount = async (id: number) => {
    await api.accounts.delete(id);
    load();
  };

  const getProfileName = (id: number) => profiles.find(p => p.id === id)?.name ?? 'Unknown';
  const getInstitutionLabel = (val: string) => INSTITUTIONS.find(i => i.value === val)?.label ?? val;

  if (loading) return <div className="p-8 text-slate-500">Loading...</div>;

  return (
    <div className="p-8 max-w-4xl">
      <h2 className="text-2xl font-bold text-slate-900 mb-1">Setup</h2>
      <p className="text-slate-500 mb-8">Add profiles for yourself and your spouse, then add your bank accounts and credit cards.</p>

      {/* Profiles */}
      <section className="mb-10">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <UserPlus size={20} /> Profiles
        </h3>
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex gap-3 mb-4">
            <input
              type="text"
              placeholder="Name"
              value={newProfile.name}
              onChange={e => setNewProfile(prev => ({ ...prev, name: e.target.value }))}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              onKeyDown={e => e.key === 'Enter' && addProfile()}
            />
            <select
              value={newProfile.role}
              onChange={e => setNewProfile(prev => ({ ...prev, role: e.target.value }))}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="self">Self</option>
              <option value="spouse">Spouse</option>
            </select>
            <button
              onClick={addProfile}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors flex items-center gap-1"
            >
              <Plus size={16} /> Add
            </button>
          </div>
          {profiles.length === 0 ? (
            <p className="text-slate-400 text-sm">No profiles yet. Add yourself and your spouse above.</p>
          ) : (
            <div className="space-y-2">
              {profiles.map(p => (
                <div key={p.id} className="flex items-center justify-between py-2 px-4 bg-slate-50 rounded-lg">
                  <div>
                    <span className="font-medium text-slate-800">{p.name}</span>
                    <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${p.role === 'self' ? 'bg-indigo-100 text-indigo-700' : 'bg-purple-100 text-purple-700'}`}>
                      {p.role}
                    </span>
                  </div>
                  <button onClick={() => deleteProfile(p.id)} className="text-slate-400 hover:text-red-500 transition-colors">
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Accounts */}
      <section>
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <CreditCard size={20} /> Bank Accounts & Credit Cards
        </h3>
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          {profiles.length === 0 ? (
            <p className="text-slate-400 text-sm">Add a profile first before adding accounts.</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <select
                  value={newAccount.profile_id}
                  onChange={e => setNewAccount(prev => ({ ...prev, profile_id: Number(e.target.value) }))}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {profiles.map(p => (
                    <option key={p.id} value={p.id}>{p.name} ({p.role})</option>
                  ))}
                </select>
                <select
                  value={newAccount.institution}
                  onChange={e => setNewAccount(prev => ({ ...prev, institution: e.target.value }))}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {INSTITUTIONS.map(i => (
                    <option key={i.value} value={i.value}>{i.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 mb-4">
                <select
                  value={newAccount.account_type}
                  onChange={e => setNewAccount(prev => ({ ...prev, account_type: e.target.value }))}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {ACCOUNT_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Account nickname"
                  value={newAccount.account_name}
                  onChange={e => setNewAccount(prev => ({ ...prev, account_name: e.target.value }))}
                  className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Last 4"
                  maxLength={4}
                  value={newAccount.last_four}
                  onChange={e => setNewAccount(prev => ({ ...prev, last_four: e.target.value }))}
                  className="w-20 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <button
                  onClick={addAccount}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors flex items-center gap-1"
                >
                  <Plus size={16} /> Add
                </button>
              </div>
            </>
          )}

          {accounts.length === 0 ? (
            <p className="text-slate-400 text-sm">No accounts yet.</p>
          ) : (
            <div className="space-y-2">
              {accounts.map(a => (
                <div key={a.id} className="flex items-center justify-between py-3 px-4 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Building2 size={18} className="text-slate-400" />
                    <div>
                      <span className="font-medium text-slate-800">{a.account_name}</span>
                      {a.last_four && <span className="text-slate-400 text-sm ml-1">****{a.last_four}</span>}
                      <div className="text-xs text-slate-500">
                        {getInstitutionLabel(a.institution)} &middot; {a.account_type.replace('_', ' ')} &middot; {getProfileName(a.profile_id)}
                      </div>
                    </div>
                  </div>
                  <button onClick={() => deleteAccount(a.id)} className="text-slate-400 hover:text-red-500 transition-colors">
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
