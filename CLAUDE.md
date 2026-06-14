# Finances Tracker — Project Instructions for Claude Code

## Critical security constraint
- **All data stays local.** Nothing in this app may call out to a cloud LLM or external service to parse, transmit, or store financial data (statements, transactions, balances, account numbers).
- Bank statement parsing must remain rule-based (section-aware state machine parsers per bank in `backend/parsers/`), never sent to an external API.
- Never commit `data/*.db`, `*.db`, `uploads/`, or any real statement PDFs — these are gitignored. Double-check before staging files.

## Environment
- Python virtual environment: `.venv-finances-tracker/` (project-specific naming convention — always use `.venv-<project-slug>`, not generic `.venv`).
- **Requires Python 3.10+** (codebase uses PEP 604 `X | None` syntax). macOS stock `python3` is often 3.9 — use Homebrew Python explicitly, e.g. `/usr/local/bin/python3.13 -m venv .venv-finances-tracker`.
- Run commands and full setup instructions: see [RUN.md](RUN.md).

## Architecture
- **Backend:** FastAPI + SQLite (`backend/`)
  - `parsers/` — one section-aware state-machine parser per bank (First Tech, Chase, Citi, Apple Card, Zolve). No loose/greedy regexes — they produce garbage matches (phone numbers, APY rates, etc.).
  - `routers/` — API endpoints (profiles, accounts, statements, transactions, analytics, export)
  - `services/` — import/dedup logic, analytics, Excel export
  - `database.py` — schema + migrations via `PRAGMA table_info` checks + `ALTER TABLE ADD COLUMN`
- **Frontend:** React + Vite + Tailwind + Recharts (`frontend/src/`)
  - `pages/` — Dashboard, Upload, Transactions, Breakdown, Setup, Coverage
  - `api/` — typed API client (`client.ts`, `types.ts`)
  - Routing via `react-router-dom`, `Layout.tsx` provides sidebar nav

## Conventions
- Category keyword matching in `backend/parsers/base.py`: check "income" category (payroll, dividend, etc.) **before** other categories so income deposits from e.g. "AMAZON.COM SVCS - PAYROLL" aren't miscategorized as "Shopping".
- Duplicate file detection: SHA-256 hash of uploaded PDF bytes, unique index `idx_stmt_file_hash`.
- Cross-account transfers are detected and excluded from spending/income totals in analytics.
- Coverage endpoint (`GET /api/statements/coverage`): for First Tech savings/certificate accounts, transactions are bundled into the checking PDF — no separate statement is expected (shown as a "note", not "missing").

## Verification before considering a change done
- Backend: `.venv-finances-tracker/bin/python -c "from backend.main import app; print('OK')"`
- Frontend: `cd frontend && npx tsc --noEmit`
