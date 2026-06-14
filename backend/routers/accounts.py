from fastapi import APIRouter
from ..database import get_db
from ..models import AccountCreate, AccountOut

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(profile_id: int | None = None):
    db = get_db()
    if profile_id:
        rows = db.execute("SELECT * FROM accounts WHERE profile_id = ? ORDER BY id", (profile_id,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM accounts ORDER BY id").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("", response_model=AccountOut)
def create_account(account: AccountCreate):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO accounts (profile_id, institution, account_type, account_name, last_four) VALUES (?, ?, ?, ?, ?)",
        (account.profile_id, account.institution, account.account_type, account.account_name, account.last_four),
    )
    db.commit()
    row = db.execute("SELECT * FROM accounts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    db.close()
    return dict(row)


@router.delete("/{account_id}")
def delete_account(account_id: int):
    db = get_db()
    db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    db.commit()
    db.close()
    return {"deleted": True}
