# Finances Tracker

A personal finance tracker that parses bank statement PDFs **entirely locally** — no cloud services, no LLM calls, nothing leaves your machine.

- **Backend:** FastAPI + SQLite
- **Frontend:** React + Vite + Tailwind + Recharts

## Features

- **Auto-detect upload** — drop any supported bank PDF and the system identifies the institution and account automatically
- **Section-aware PDF parsers** (no LLM) for:
  - First Tech (checking + savings/certificates + credit card)
  - Chase (checking, Amazon Visa, Sapphire)
  - Citi (Costco Visa)
  - Zolve credit card (supports password-protected PDFs)
  - Apple Card
- **Duplicate file detection** — re-uploading the same statement is caught via SHA-256 file hashing
- **Validation** — parsed totals are checked against the statement's own summary section
- **Transfer dedup** — cross-account transfers are detected and excluded from spending totals
- **Coverage view** — per-profile, per-month grid showing which accounts have statements uploaded vs. missing
- **Dashboard** — income/spending/savings trends, category breakdown, account breakdown
- **Breakdown** — drill into a category → merchants → individual transactions
- **Transaction CRUD** — filter, sort, edit, delete, recategorize
- **Excel export** — export transactions for a given period
- **Multi-profile support** — track multiple people's accounts (e.g. you + spouse) separately

## Getting Started

See [RUN.md](RUN.md) for the full setup and run cheat sheet, including:

- Quick start commands
- First-time environment setup (Python 3.10+ venv, npm install)
- Project layout
- Common tasks (resetting the DB, adding dependencies, etc.)
- Troubleshooting

## Privacy

All data is stored locally in `data/finance.db`. Uploaded PDFs are stored in `uploads/`. Both are excluded from version control via `.gitignore`. Nothing is ever sent to a third party.
