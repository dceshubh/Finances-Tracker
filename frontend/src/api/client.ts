import type { Profile, Account, Statement, Transaction, UploadResult, DashboardData, TimePeriodData, CategoryBreakdown, MerchantTransaction, CoverageData } from './types';

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  profiles: {
    list: () => request<Profile[]>('/profiles'),
    create: (data: { name: string; role: string }) =>
      request<Profile>('/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    delete: (id: number) => request<void>(`/profiles/${id}`, { method: 'DELETE' }),
  },

  accounts: {
    list: (profileId?: number) =>
      request<Account[]>(`/accounts${profileId ? `?profile_id=${profileId}` : ''}`),
    create: (data: { profile_id: number; institution: string; account_type: string; account_name: string; last_four?: string }) =>
      request<Account>('/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    delete: (id: number) => request<void>(`/accounts/${id}`, { method: 'DELETE' }),
  },

  statements: {
    list: (accountId?: number) =>
      request<Statement[]>(`/statements${accountId ? `?account_id=${accountId}` : ''}`),
    upload: async (file: File, accountId?: number, institutionHint?: string, password?: string): Promise<UploadResult> => {
      const formData = new FormData();
      formData.append('file', file);
      if (accountId) formData.append('account_id', String(accountId));
      if (institutionHint) formData.append('institution_hint', institutionHint);
      if (password) formData.append('password', password);
      return request<UploadResult>('/statements/upload', { method: 'POST', body: formData });
    },
    delete: (id: number) => request<{ deleted: boolean; transactions_deleted: number; filename: string }>(`/statements/${id}`, { method: 'DELETE' }),
    coverage: (months?: number) =>
      request<CoverageData>(`/statements/coverage${months !== undefined ? `?months=${months}` : ''}`),
  },

  transactions: {
    list: (params?: {
      account_id?: number; profile_id?: number; category?: string;
      tx_type?: string; date_from?: string; date_to?: string;
      sort_by?: string; sort_dir?: string; limit?: number; offset?: number;
    }) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) searchParams.set(k, String(v));
        });
      }
      const qs = searchParams.toString();
      return request<Transaction[]>(`/transactions${qs ? `?${qs}` : ''}`);
    },
    count: (params?: {
      account_id?: number; profile_id?: number; category?: string;
      tx_type?: string; date_from?: string; date_to?: string;
    }) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) searchParams.set(k, String(v));
        });
      }
      const qs = searchParams.toString();
      return request<{ count: number }>(`/transactions/count${qs ? `?${qs}` : ''}`);
    },
    update: (id: number, data: { description?: string; amount?: number; category?: string; tx_type?: string; date?: string }) =>
      request<Transaction>(`/transactions/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    delete: (id: number) => request<void>(`/transactions/${id}`, { method: 'DELETE' }),
    deleteAll: (params?: { profile_id?: number; account_id?: number }) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) searchParams.set(k, String(v));
        });
      }
      const qs = searchParams.toString();
      return request<void>(`/transactions${qs ? `?${qs}` : ''}`, { method: 'DELETE' });
    },
  },

  analytics: {
    dashboard: (params?: { profile_id?: number; year?: number; month?: number }) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) searchParams.set(k, String(v));
        });
      }
      const qs = searchParams.toString();
      return request<DashboardData>(`/analytics/dashboard${qs ? `?${qs}` : ''}`);
    },
    weekly: (params?: { profile_id?: number; year?: number }) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) searchParams.set(k, String(v));
        });
      }
      const qs = searchParams.toString();
      return request<TimePeriodData[]>(`/analytics/weekly${qs ? `?${qs}` : ''}`);
    },
    daily: (params?: { profile_id?: number; year?: number; month?: number }) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) searchParams.set(k, String(v));
        });
      }
      const qs = searchParams.toString();
      return request<TimePeriodData[]>(`/analytics/daily${qs ? `?${qs}` : ''}`);
    },
    yearly: (params?: { profile_id?: number }) => {
      const searchParams = new URLSearchParams();
      if (params?.profile_id) searchParams.set('profile_id', String(params.profile_id));
      const qs = searchParams.toString();
      return request<TimePeriodData[]>(`/analytics/yearly${qs ? `?${qs}` : ''}`);
    },
    breakdown: (params?: { profile_id?: number; year?: number; month?: number; tx_type?: string }) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) searchParams.set(k, String(v));
        });
      }
      const qs = searchParams.toString();
      return request<CategoryBreakdown[]>(`/analytics/breakdown${qs ? `?${qs}` : ''}`);
    },
    merchantTransactions: (params: { description: string; profile_id?: number; year?: number; month?: number; tx_type?: string }) => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) searchParams.set(k, String(v));
      });
      const qs = searchParams.toString();
      return request<MerchantTransaction[]>(`/analytics/merchant-transactions?${qs}`);
    },
  },
};
