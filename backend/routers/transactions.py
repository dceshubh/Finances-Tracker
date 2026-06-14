from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_db
from ..models import TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


class TransactionUpdate(BaseModel):
    description: str | None = None
    amount: float | None = None
    category: str | None = None
    tx_type: str | None = None
    date: str | None = None


@router.get("/count")
def count_transactions(
    account_id: int | None = None,
    profile_id: int | None = None,
    category: str | None = None,
    tx_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    db = get_db()
    query = "SELECT COUNT(*) FROM transactions t"
    conditions = []
    params: list = []

    if profile_id:
        query += " JOIN accounts a ON t.account_id = a.id"
        conditions.append("a.profile_id = ?")
        params.append(profile_id)

    if account_id:
        conditions.append("t.account_id = ?")
        params.append(account_id)
    if category:
        conditions.append("t.category = ?")
        params.append(category)
    if tx_type:
        conditions.append("t.tx_type = ?")
        params.append(tx_type)
    if date_from:
        conditions.append("t.date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("t.date <= ?")
        params.append(date_to)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    count = db.execute(query, params).fetchone()[0]
    db.close()
    return {"count": count}


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    account_id: int | None = None,
    profile_id: int | None = None,
    category: str | None = None,
    tx_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    db = get_db()
    query = "SELECT t.* FROM transactions t"
    conditions = []
    params: list = []

    if profile_id:
        query += " JOIN accounts a ON t.account_id = a.id"
        conditions.append("a.profile_id = ?")
        params.append(profile_id)

    if account_id:
        conditions.append("t.account_id = ?")
        params.append(account_id)

    if category:
        conditions.append("t.category = ?")
        params.append(category)

    if tx_type:
        conditions.append("t.tx_type = ?")
        params.append(tx_type)

    if date_from:
        conditions.append("t.date >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("t.date <= ?")
        params.append(date_to)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Sorting
    allowed_sort = {"date": "t.date", "amount": "t.amount", "description": "t.description", "category": "t.category"}
    order_col = allowed_sort.get(sort_by, "t.date")
    order_dir = "ASC" if sort_dir == "asc" else "DESC"
    query += f" ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.put("/{tx_id}")
def update_transaction(tx_id: int, update: TransactionUpdate):
    db = get_db()
    existing = db.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not existing:
        db.close()
        raise HTTPException(status_code=404, detail="Transaction not found")

    fields = []
    params = []
    if update.description is not None:
        fields.append("description = ?")
        params.append(update.description)
    if update.amount is not None:
        fields.append("amount = ?")
        params.append(update.amount)
    if update.category is not None:
        fields.append("category = ?")
        params.append(update.category)
    if update.tx_type is not None:
        fields.append("tx_type = ?")
        params.append(update.tx_type)
    if update.date is not None:
        fields.append("date = ?")
        params.append(update.date)

    if not fields:
        db.close()
        return {"updated": False, "reason": "No fields to update"}

    params.append(tx_id)
    db.execute(f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?", params)
    db.commit()
    row = db.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    db.close()
    return dict(row)


@router.delete("/{tx_id}")
def delete_transaction(tx_id: int):
    db = get_db()
    existing = db.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not existing:
        db.close()
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    db.commit()
    db.close()
    return {"deleted": True}


@router.delete("")
def delete_all_transactions(profile_id: int | None = None, account_id: int | None = None):
    """Delete all transactions, optionally filtered by profile or account."""
    db = get_db()
    if account_id:
        db.execute("DELETE FROM transactions WHERE account_id = ?", (account_id,))
    elif profile_id:
        db.execute("DELETE FROM transactions WHERE account_id IN (SELECT id FROM accounts WHERE profile_id = ?)", (profile_id,))
    else:
        db.execute("DELETE FROM transactions")
    db.execute("DELETE FROM statements")
    db.commit()
    db.close()
    return {"deleted": True}
