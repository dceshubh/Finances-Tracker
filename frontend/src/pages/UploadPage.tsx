import { useEffect, useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { api } from '../api/client';
import type { Account, Statement, UploadResult } from '../api/types';
import { Upload, FileText, CheckCircle2, XCircle, Clock, Loader2, AlertTriangle, Trash2, ShieldCheck, ShieldAlert, Lock, X } from 'lucide-react';

export default function UploadPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  // Two-step upload state
  const [stagedFile, setStagedFile] = useState<File | null>(null);
  const [needsPassword, setNeedsPassword] = useState(false);
  const [password, setPassword] = useState('');
  const passwordRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    const [a, s] = await Promise.all([api.accounts.list(), api.statements.list()]);
    setAccounts(a);
    setStatements(s);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const doUpload = async (file: File, pwd?: string) => {
    setUploading(true);
    setResult(null);

    try {
      const res = await api.statements.upload(file, undefined, undefined, pwd || undefined);

      if (!res.success && res.error === 'password_required') {
        // PDF is encrypted — prompt for password
        setStagedFile(file);
        setNeedsPassword(true);
        setPassword('');
        setResult(null);
        // Focus password input after render
        setTimeout(() => passwordRef.current?.focus(), 100);
      } else {
        // Success or other error — show result, clear staged file
        setResult(res);
        setStagedFile(null);
        setNeedsPassword(false);
        setPassword('');
        load();
      }
    } catch (err: any) {
      setResult({ success: false, error: err.message });
      setStagedFile(null);
      setNeedsPassword(false);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    // First attempt: no password
    doUpload(file);
  }, []);

  const handlePasswordSubmit = () => {
    if (!stagedFile || !password.trim()) return;
    doUpload(stagedFile, password.trim());
  };

  const handleCancelPassword = () => {
    setStagedFile(null);
    setNeedsPassword(false);
    setPassword('');
    setResult(null);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: uploading || needsPassword,
  });

  const getAccountLabel = (id: number) => {
    const a = accounts.find(acc => acc.id === id);
    return a ? `${a.account_name} (${a.institution.replace('_', ' ')})` : 'Unknown';
  };

  const handleDelete = async (statementId: number) => {
    try {
      await api.statements.delete(statementId);
      setDeleteConfirm(null);
      load();
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`);
    }
  };

  const fmt = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });

  if (loading) return <div className="p-8 text-slate-500">Loading...</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-slate-900 mb-1">Upload Statements</h2>
      <p className="text-slate-500 mb-8">
        Drop any bank statement PDF. The system auto-detects the bank and account, then validates parsed totals against the statement summary.
      </p>

      {accounts.length === 0 ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-amber-800">
          No accounts set up yet. Go to <strong>Setup</strong> to add your bank accounts first.
        </div>
      ) : (
        <>
          {/* Dropzone — disabled when waiting for password */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
              needsPassword
                ? 'border-slate-200 bg-slate-50 cursor-not-allowed opacity-50'
                : isDragActive
                ? 'border-indigo-500 bg-indigo-50'
                : uploading
                ? 'border-slate-300 bg-slate-50 cursor-wait'
                : 'border-slate-300 hover:border-indigo-400 hover:bg-indigo-50/50 cursor-pointer'
            }`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={40} className="text-indigo-500 animate-spin" />
                <p className="text-slate-600 font-medium">Detecting bank & parsing transactions...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <Upload size={40} className="text-slate-400" />
                <p className="text-slate-600 font-medium">
                  {isDragActive ? 'Drop PDF here' : 'Drag & drop a PDF statement, or click to browse'}
                </p>
                <p className="text-sm text-slate-400">Auto-detects: Chase, Citi, Apple Card, First Tech, Zolve</p>
              </div>
            )}
          </div>

          {/* Password prompt — shown only when PDF is encrypted */}
          {needsPassword && stagedFile && (
            <div className="mt-4 bg-amber-50 border border-amber-300 rounded-xl p-5 animate-in fade-in">
              <div className="flex items-start gap-3">
                <Lock size={20} className="text-amber-600 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <h4 className="font-semibold text-amber-800">Password Required</h4>
                  <p className="text-sm text-amber-700 mt-1">
                    <strong>{stagedFile.name}</strong> is encrypted. Enter the PDF password to continue.
                  </p>
                  <div className="mt-3 flex items-center gap-3">
                    <input
                      ref={passwordRef}
                      type="password"
                      placeholder="Enter PDF password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') handlePasswordSubmit(); }}
                      className="flex-1 max-w-xs px-3 py-2 text-sm border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent"
                      autoFocus
                    />
                    <button
                      onClick={handlePasswordSubmit}
                      disabled={!password.trim() || uploading}
                      className="px-4 py-2 text-sm font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {uploading ? (
                        <span className="flex items-center gap-2">
                          <Loader2 size={14} className="animate-spin" /> Uploading...
                        </span>
                      ) : 'Upload'}
                    </button>
                    <button
                      onClick={handleCancelPassword}
                      className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
                      title="Cancel"
                    >
                      <X size={18} />
                    </button>
                  </div>
                  <p className="text-xs text-amber-600 mt-2">
                    Tip: For Zolve statements, the password is the first 4 characters of your first name in CAPS followed by year of birth in yyYY format.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Duplicate file detected — special-case banner */}
          {result && !result.success && result.error === 'duplicate_file' && result.duplicate && (
            <div className="mt-6 rounded-xl border bg-blue-50 border-blue-200 p-6">
              <div className="flex items-start gap-3">
                <FileText size={24} className="text-blue-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-blue-800">Already Uploaded</h4>
                  <p className="mt-1 text-sm text-blue-700">
                    This exact PDF has already been imported. No new transactions were added.
                  </p>
                  <div className="mt-3 p-3 rounded-lg bg-white/60 border border-blue-200 text-sm space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Filename:</span>
                      <span className="font-medium text-slate-800">{result.duplicate.filename}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Account:</span>
                      <span className="font-medium text-slate-800">
                        {result.duplicate.account_name} ({result.duplicate.institution.replace('_', ' ')})
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Uploaded:</span>
                      <span className="font-medium text-slate-800">
                        {new Date(result.duplicate.uploaded_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Transactions:</span>
                      <span className="font-medium text-slate-800">{result.duplicate.transaction_count}</span>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-blue-600">
                    To re-import, first delete the existing statement from Upload History below.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Upload Result — skip when duplicate file (handled above) */}
          {result && !(result.error === 'duplicate_file') && (
            <div className={`mt-6 rounded-xl border p-6 ${
              result.success
                ? result.validation?.status === 'mismatch'
                  ? 'bg-amber-50 border-amber-200'
                  : 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-start gap-3">
                {result.success ? (
                  result.validation?.status === 'mismatch' ? (
                    <AlertTriangle size={24} className="text-amber-600 mt-0.5" />
                  ) : (
                    <CheckCircle2 size={24} className="text-green-600 mt-0.5" />
                  )
                ) : (
                  <XCircle size={24} className="text-red-600 mt-0.5" />
                )}
                <div className="flex-1">
                  <h4 className={`font-semibold ${
                    result.success
                      ? result.validation?.status === 'mismatch' ? 'text-amber-800' : 'text-green-800'
                      : 'text-red-800'
                  }`}>
                    {result.success
                      ? result.validation?.status === 'mismatch'
                        ? 'Parsed with Warnings'
                        : 'Upload Successful'
                      : 'Upload Failed'}
                  </h4>

                  {result.success ? (
                    <div className="mt-2 text-sm space-y-1">
                      <div className="text-slate-700">
                        <p>Detected: <strong>{result.detected_institution?.replace('_', ' ')}</strong>
                          {result.detected_account && <> &rarr; <strong>{result.detected_account}</strong></>}
                        </p>
                        <p>Parsed: <strong>{result.total_parsed}</strong> transactions &middot;
                          New: <strong>{result.transactions_inserted}</strong> &middot;
                          Duplicates skipped: <strong>{result.duplicates_skipped}</strong>
                        </p>
                        {result.period_start && result.period_end && (
                          <p>Period: {result.period_start} to {result.period_end}</p>
                        )}
                      </div>

                      {/* Validation Report */}
                      {result.validation && result.validation.checks.length > 0 && (
                        <div className={`mt-3 p-3 rounded-lg border ${
                          result.validation.status === 'ok'
                            ? 'bg-green-100/50 border-green-300'
                            : 'bg-amber-100/50 border-amber-300'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            {result.validation.status === 'ok' ? (
                              <ShieldCheck size={16} className="text-green-600" />
                            ) : (
                              <ShieldAlert size={16} className="text-amber-600" />
                            )}
                            <span className={`font-semibold text-xs uppercase tracking-wider ${
                              result.validation.status === 'ok' ? 'text-green-700' : 'text-amber-700'
                            }`}>
                              {result.validation.status === 'ok' ? 'Validation Passed' : 'Validation Mismatch'}
                            </span>
                            <span className="text-xs text-slate-500 ml-auto">{result.validation.source}</span>
                          </div>
                          <div className="space-y-1">
                            {result.validation.checks.map((check: any, i: number) => (
                              <div key={i} className="flex items-center justify-between text-xs">
                                <span className="text-slate-600">{check.label}</span>
                                <div className="flex items-center gap-3">
                                  <span className="text-slate-500">
                                    Expected: <strong>{fmt(check.expected)}</strong>
                                  </span>
                                  <span className="text-slate-500">
                                    Parsed: <strong>{fmt(check.parsed)}</strong>
                                  </span>
                                  {check.match ? (
                                    <CheckCircle2 size={14} className="text-green-600" />
                                  ) : (
                                    <XCircle size={14} className="text-red-500" />
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.validation && result.validation.checks.length === 0 && (
                        <div className="mt-3 p-3 rounded-lg border bg-slate-50 border-slate-200">
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                            <ShieldCheck size={14} className="text-slate-400" />
                            <span>No summary totals available for cross-validation on this statement type</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="mt-1 text-sm text-red-700">{result.error}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Upload History */}
      {statements.length > 0 && (
        <section className="mt-10">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Upload History</h3>
          <div className="space-y-3">
            {statements.map(s => (
              <div key={s.id} className={`bg-white rounded-lg border overflow-hidden ${
                deleteConfirm === s.id ? 'border-red-300' : 'border-slate-200'
              }`}>
                <div className="px-4 py-3 flex items-center gap-3 hover:bg-slate-50 group">
                  <FileText size={18} className="text-slate-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-slate-800 text-sm" title={s.filename}>{s.filename}</span>
                      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full shrink-0 ${
                        s.status === 'parsed' ? 'bg-green-100 text-green-700' :
                        s.status === 'warning' ? 'bg-amber-100 text-amber-700' :
                        s.status === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {s.status === 'parsed' ? <CheckCircle2 size={12} /> :
                         s.status === 'warning' ? <AlertTriangle size={12} /> :
                         s.status === 'failed' ? <XCircle size={12} /> :
                         <Clock size={12} />}
                        {s.status}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {getAccountLabel(s.account_id)}
                      {s.period_start && s.period_end && (
                        <span className="ml-2">{s.period_start} — {s.period_end}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setDeleteConfirm(deleteConfirm === s.id ? null : s.id)}
                    className="text-slate-300 hover:text-red-500 transition-colors p-1 shrink-0"
                    title="Delete statement and all its transactions"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                {deleteConfirm === s.id && (
                  <div className="px-4 py-2 bg-red-50 border-t border-red-200 flex items-center gap-3 flex-wrap">
                    <span className="text-xs text-red-700">Delete this statement and all its transactions?</span>
                    <button
                      onClick={() => handleDelete(s.id)}
                      className="text-xs px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
                    >
                      Delete
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="text-xs px-3 py-1 bg-white text-slate-600 rounded border border-slate-300 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
