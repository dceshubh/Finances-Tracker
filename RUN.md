# Finances Tracker — Run Cheat Sheet

A personal finance tracker that parses bank statement PDFs locally (no cloud, no LLM). Backend: FastAPI + SQLite. Frontend: React + Vite + Tailwind.

---

## 🚀 Quick Start (every time you want to use the app)

Open **two terminals**.

### Terminal 1 — Backend
```bash
cd "/Users/shubhamvarshney/Desktop/Education/CapstoneProjects/Finances Tracker"
source .venv-finances-tracker/bin/activate
uvicorn backend.main:app --reload --port 8000
```

### Terminal 2 — Frontend
```bash
cd "/Users/shubhamvarshney/Desktop/Education/CapstoneProjects/Finances Tracker/frontend"
npm run dev
```

Open **http://localhost:5173** in your browser. Done.

To stop: `Ctrl+C` in each terminal.

---

## 📍 URLs

| What | URL |
|---|---|
| App | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

---

## 🗂️ Project Layout

```
Finances Tracker/
├── .venv-finances-tracker/              # Python virtual environment (don't commit)
├── backend/            # FastAPI app, parsers, services
│   ├── main.py         # Entry point — uvicorn loads this
│   ├── parsers/        # Bank-specific PDF parsers
│   ├── routers/        # API endpoints
│   └── services/       # Business logic (import, analytics, export)
├── frontend/           # React + Vite app
│   ├── src/pages/      # Dashboard, Upload, Transactions, Breakdown, Setup
│   └── src/api/        # API client + types
├── data/
│   └── finance.db      # SQLite database (your data lives here)
├── uploads/            # Saved PDF copies
├── requirements.txt    # Python deps (for reproducibility)
└── RUN.md              # This file
```

---

## 🛠️ First-Time Setup (only if rebuilding from scratch)

> **Python 3.10+ required.** The codebase uses PEP 604 syntax (`int | None`) which doesn't work on macOS's stock Python 3.9. Use Homebrew Python: `/usr/local/bin/python3.13`.

```bash
# Backend
cd "/Users/shubhamvarshney/Desktop/Education/CapstoneProjects/Finances Tracker"
/usr/local/bin/python3.13 -m venv .venv-finances-tracker
source .venv-finances-tracker/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

---

## 🔧 Common Tasks

### Add new Python dependency
```bash
source .venv-finances-tracker/bin/activate
pip install <package>
pip freeze > requirements.txt    # update lockfile
```

### Add new Node dependency
```bash
cd frontend
npm install <package>
```

### Reset the database (⚠️ wipes all transactions)
```bash
rm "/Users/shubhamvarshney/Desktop/Education/CapstoneProjects/Finances Tracker/data/finance.db"
# Restart backend — schema auto-creates on next run
```

### See what's in the database quickly
```bash
sqlite3 "/Users/shubhamvarshney/Desktop/Education/CapstoneProjects/Finances Tracker/data/finance.db"
sqlite> .tables
sqlite> SELECT * FROM accounts;
sqlite> .quit
```

### Run backend without activating venv
```bash
cd "/Users/shubhamvarshney/Desktop/Education/CapstoneProjects/Finances Tracker"
.venv-finances-tracker/bin/uvicorn backend.main:app --reload --port 8000
```

### Kill processes if ports are stuck
```bash
lsof -ti:8000 | xargs kill    # backend port
lsof -ti:5173 | xargs kill    # frontend port
```

---

## 💼 Using the App

1. **Setup** → Add your profile(s) and bank accounts
2. **Upload** → Drag any bank PDF; system auto-detects bank + account
   - For encrypted PDFs (Zolve), enter password when prompted
   - Zolve password format: first 4 chars of first name in CAPS + birth year (yyYY)
3. **Dashboard** → Monthly income, spending, net savings, charts
4. **Transactions** → Filter, sort, edit, delete; categorize manually
5. **Breakdown** → Drill into categories → merchants → individual transactions
6. **Coverage** → See which months/accounts have statements uploaded vs. missing, per profile

Supported banks: **Chase** (checking, Sapphire, Amazon), **Citi Costco**, **Apple Card**, **First Tech** (checking, savings, CC, certificates), **Zolve**.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: uvicorn` | Forgot to `source .venv-finances-tracker/bin/activate` |
| `TypeError: unsupported operand type(s) for \|: 'type' and 'NoneType'` | Venv built on Python 3.9. Recreate with 3.10+: `rm -rf .venv-finances-tracker && /usr/local/bin/python3.13 -m venv .venv-finances-tracker && source .venv-finances-tracker/bin/activate && pip install -r requirements.txt` |
| Frontend can't reach backend | Backend not running, or wrong port (must be 8000) |
| Upload says "Could not detect bank" | Account isn't set up — go to Setup tab first |
| Upload says password required | PDF is encrypted — enter password in the prompt |
| Validation mismatch warning | Parsed totals don't match statement summary; check Transactions for missing rows |
| Wrong category on a transaction | Edit it inline in the Transactions page; future statements with same merchant won't auto-fix unless added to `backend/parsers/base.py` `CATEGORY_KEYWORDS` |
| Port 8000 / 5173 already in use | `lsof -ti:<port> \| xargs kill` |

---

## 🔐 Privacy Note

**Everything is local.** PDFs are parsed on your machine. No data ever leaves the system. The SQLite DB lives in `data/finance.db`. Back that file up if you want to preserve your transaction history.
