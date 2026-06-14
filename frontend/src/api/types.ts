export interface Profile {
  id: number;
  name: string;
  role: 'self' | 'spouse';
  created_at: string;
}

export interface Account {
  id: number;
  profile_id: number;
  institution: string;
  account_type: 'checking' | 'savings' | 'credit_card';
  account_name: string;
  last_four: string | null;
  created_at: string;
}

export interface Statement {
  id: number;
  account_id: number;
  filename: string;
  period_start: string | null;
  period_end: string | null;
  uploaded_at: string;
  status: 'pending' | 'parsed' | 'failed' | 'warning';
  error_message: string | null;
}

export interface Transaction {
  id: number;
  account_id: number;
  statement_id: number | null;
  date: string;
  description: string;
  amount: number;
  tx_type: 'credit' | 'debit';
  category: string;
}

export interface ValidationCheck {
  label: string;
  expected: number;
  parsed: number;
  match: boolean;
}

export interface ValidationReport {
  status: 'ok' | 'mismatch' | 'no_validation';
  checks: ValidationCheck[];
  source: string;
  parsed_credit_total: number;
  parsed_debit_total: number;
}

export interface DuplicateInfo {
  statement_id: number;
  filename: string;
  uploaded_at: string;
  account_name: string;
  institution: string;
  transaction_count: number;
}

export interface UploadResult {
  success: boolean;
  error?: string;
  statement_id?: number;
  detected_institution?: string;
  detected_account?: string;
  detected_account_id?: number;
  detected_account_type?: string;
  detected_last_four?: string;
  transactions_inserted?: number;
  duplicates_skipped?: number;
  total_parsed?: number;
  period_start?: string | null;
  period_end?: string | null;
  validation?: ValidationReport | null;
  duplicate?: DuplicateInfo;
}

export interface DashboardData {
  total_income: number;
  total_spending: number;
  net_savings: number;
  total_transfers: number;
  monthly_trend: { month: string; income: number; spending: number; transfers?: number }[];
  category_breakdown: { category: string; total: number }[];
  account_breakdown: { account_name: string; institution: string; account_type: string; income: number; spending: number; transfers?: number }[];
  recent_transactions: (Transaction & { account_name: string; institution: string })[];
}

export interface TimePeriodData {
  income: number;
  spending: number;
  [key: string]: string | number;
}

export interface MerchantDetail {
  description: string;
  total: number;
  count: number;
}

export interface CategoryBreakdown {
  category: string;
  total: number;
  count: number;
  merchants: MerchantDetail[];
}

export interface MerchantTransaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  tx_type: string;
  category: string;
  account_name: string;
}

export interface CoverageCell {
  status: 'uploaded' | 'warning' | 'missing';
  statement_id?: number;
  filename?: string;
}

export interface CoverageAccount {
  account_id: number;
  account_name: string;
  institution: string;
  account_type: 'checking' | 'savings' | 'credit_card';
  last_four: string | null;
  note: string | null;
  coverage: Record<string, CoverageCell>;
}

export interface CoverageProfile {
  profile_id: number;
  profile_name: string;
  accounts: CoverageAccount[];
}

export interface CoverageData {
  months: string[];
  profiles: CoverageProfile[];
}

export const INSTITUTIONS = [
  { value: 'chase', label: 'Chase' },
  { value: 'citi', label: 'Citi' },
  { value: 'apple_card', label: 'Apple Card' },
  { value: 'first_tech', label: 'First Tech' },
  { value: 'zolve', label: 'Zolve' },
] as const;

export const ACCOUNT_TYPES = [
  { value: 'checking', label: 'Checking' },
  { value: 'savings', label: 'Savings' },
  { value: 'credit_card', label: 'Credit Card' },
] as const;
