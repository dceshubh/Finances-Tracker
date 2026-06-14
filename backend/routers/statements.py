import shutil
import hashlib
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..database import get_db
from ..services.import_service import import_statement, import_statement_auto
from ..models import StatementOut


def _hash_file(path: Path) -> str:
    """SHA-256 of a file's bytes, streamed in 64KB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

router = APIRouter(prefix="/api/statements", tags=["statements"])
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"


@router.get("", response_model=list[StatementOut])
def list_statements(account_id: int | None = None):
    db = get_db()
    if account_id:
        rows = db.execute("SELECT * FROM statements WHERE account_id = ? ORDER BY uploaded_at DESC", (account_id,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM statements ORDER BY uploaded_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/coverage")
def get_coverage(months: int | None = None):
    """For each profile/account, report which months have an uploaded statement
    and which are missing, across the full date range seen in the data
    (optionally extended forward by `months` extra trailing months)."""
    import calendar
    from datetime import date

    db = get_db()

    # Determine overall month range from non-failed statements
    bounds = db.execute(
        "SELECT MIN(period_start) as mn, MAX(period_end) as mx FROM statements WHERE status != 'failed' AND period_start IS NOT NULL"
    ).fetchone()

    if not bounds["mn"] or not bounds["mx"]:
        db.close()
        return {"months": [], "profiles": []}

    mn = date.fromisoformat(bounds["mn"])
    mx = date.fromisoformat(bounds["mx"])

    # Build list of YYYY-MM strings from mn's month to mx's month
    month_list = []
    y, m = mn.year, mn.month
    while (y, m) <= (mx.year, mx.month):
        month_list.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1

    # Optionally extend forward by N extra months (e.g. to include current month)
    if months:
        ey, em = mx.year, mx.month
        for _ in range(months):
            em += 1
            if em > 12:
                em = 1
                ey += 1
            month_list.append(f"{ey:04d}-{em:02d}")

    def month_bounds(yyyymm: str):
        y, m = map(int, yyyymm.split("-"))
        start = date(y, m, 1)
        end = date(y, m, calendar.monthrange(y, m)[1])
        return start.isoformat(), end.isoformat()

    profiles = db.execute("SELECT * FROM profiles ORDER BY id").fetchall()
    result_profiles = []

    for p in profiles:
        accounts = db.execute("SELECT * FROM accounts WHERE profile_id = ? ORDER BY id", (p["id"],)).fetchall()
        account_results = []

        for a in accounts:
            # All non-failed statements for this account
            stmts = db.execute(
                "SELECT id, filename, period_start, period_end, status FROM statements "
                "WHERE account_id = ? AND status != 'failed' AND period_start IS NOT NULL AND period_end IS NOT NULL",
                (a["id"],)
            ).fetchall()

            coverage = {}
            for ym in month_list:
                m_start, m_end = month_bounds(ym)
                match = None
                for s in stmts:
                    # Overlap test: statement period intersects this calendar month
                    if s["period_start"] <= m_end and s["period_end"] >= m_start:
                        match = s
                        break
                if match:
                    coverage[ym] = {
                        "status": "warning" if match["status"] == "warning" else "uploaded",
                        "statement_id": match["id"],
                        "filename": match["filename"],
                    }
                else:
                    coverage[ym] = {"status": "missing"}

            # First Tech savings accounts don't get separate statements —
            # their transactions are bundled inside the checking PDF.
            note = None
            if a["institution"] == "first_tech" and a["account_type"] == "savings":
                sibling_checking = db.execute(
                    "SELECT COUNT(*) as c FROM statements s "
                    "JOIN accounts a2 ON a2.id = s.account_id "
                    "WHERE a2.profile_id = ? AND a2.institution = 'first_tech' AND a2.account_type = 'checking' "
                    "AND s.status != 'failed'",
                    (p["id"],)
                ).fetchone()["c"]
                if sibling_checking > 0:
                    note = "Bundled with First Tech Checking statement"

            account_results.append({
                "account_id": a["id"],
                "account_name": a["account_name"],
                "institution": a["institution"],
                "account_type": a["account_type"],
                "last_four": a["last_four"],
                "note": note,
                "coverage": coverage,
            })

        result_profiles.append({
            "profile_id": p["id"],
            "profile_name": p["name"],
            "accounts": account_results,
        })

    db.close()
    return {"months": month_list, "profiles": result_profiles}


@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    account_id: int | None = Form(None),
    institution_hint: str | None = Form(None),
    password: str | None = Form(None),
):
    """Upload a PDF statement. If account_id is provided, uses that account.
    Otherwise, auto-detects the institution and account from the PDF content.
    For encrypted PDFs (e.g., Zolve), pass the password."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    prefix = account_id or "auto"
    file_path = UPLOAD_DIR / f"{prefix}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # --- Duplicate file detection ---
    # Hash the saved PDF bytes. If we've seen this exact file before, reject upfront.
    file_hash = _hash_file(file_path)
    db = get_db()
    existing = db.execute(
        """SELECT s.id, s.filename, s.uploaded_at, s.account_id,
                  a.account_name, a.institution,
                  (SELECT COUNT(*) FROM transactions WHERE statement_id = s.id) as tx_count
           FROM statements s
           JOIN accounts a ON a.id = s.account_id
           WHERE s.file_hash = ?""",
        (file_hash,)
    ).fetchone()
    db.close()
    if existing:
        # Don't keep a duplicate copy of the same bytes on disk
        try:
            file_path.unlink()
        except OSError:
            pass
        return {
            "success": False,
            "error": "duplicate_file",
            "duplicate": {
                "statement_id": existing["id"],
                "filename": existing["filename"],
                "uploaded_at": existing["uploaded_at"],
                "account_name": existing["account_name"],
                "institution": existing["institution"],
                "transaction_count": existing["tx_count"],
            },
        }

    # Normalize empty string password to None
    pwd = password.strip() if password else None

    try:
        if account_id:
            result = import_statement(account_id, str(file_path), institution_hint, password=pwd, file_hash=file_hash)
        else:
            result = import_statement_auto(str(file_path), password=pwd, file_hash=file_hash)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Server error: {str(e)}"}


@router.delete("/{statement_id}")
def delete_statement(statement_id: int):
    """Delete a statement and ALL its associated transactions."""
    db = get_db()

    # Check statement exists
    stmt = db.execute("SELECT id, filename FROM statements WHERE id = ?", (statement_id,)).fetchone()
    if not stmt:
        db.close()
        raise HTTPException(status_code=404, detail="Statement not found")

    # Count transactions that will be deleted
    count = db.execute("SELECT COUNT(*) as c FROM transactions WHERE statement_id = ?", (statement_id,)).fetchone()["c"]

    # Delete transactions first, then statement
    db.execute("DELETE FROM transactions WHERE statement_id = ?", (statement_id,))
    db.execute("DELETE FROM statements WHERE id = ?", (statement_id,))
    db.commit()
    db.close()

    return {"deleted": True, "transactions_deleted": count, "filename": stmt["filename"]}
