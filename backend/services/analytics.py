from ..database import get_db

# Transfer category is excluded from income/spending totals to avoid double-counting
# credit card payments that appear on both checking and CC statements.
_TRANSFER_EXCLUDE = "AND t.category != 'transfer'"
_TRANSFER_CASE = """
    SUM(CASE WHEN category = 'transfer' THEN amount ELSE 0 END) as transfers
"""


def get_dashboard_data(profile_id: int | None = None, year: int | None = None, month: int | None = None):
    db = get_db()

    account_filter = ""
    params: list = []
    if profile_id:
        account_filter = "AND t.account_id IN (SELECT id FROM accounts WHERE profile_id = ?)"
        params.append(profile_id)

    date_filter = ""
    if year and month:
        date_filter = "AND strftime('%Y', t.date) = ? AND strftime('%m', t.date) = ?"
        params.extend([str(year), f"{month:02d}"])
    elif year:
        date_filter = "AND strftime('%Y', t.date) = ?"
        params.append(str(year))

    # Income: credits excluding transfers
    total_income = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM transactions t WHERE tx_type = 'credit' {_TRANSFER_EXCLUDE} {account_filter} {date_filter}",
        params,
    ).fetchone()[0]

    # Spending: debits excluding transfers
    total_spending = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM transactions t WHERE tx_type = 'debit' {_TRANSFER_EXCLUDE} {account_filter} {date_filter}",
        params,
    ).fetchone()[0]

    # Internal transfers (both directions)
    total_transfers = db.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM transactions t WHERE category = 'transfer' {account_filter} {date_filter}",
        params,
    ).fetchone()[0]

    # Monthly trend (excluding transfers)
    monthly_trend = db.execute(
        f"""SELECT strftime('%Y-%m', t.date) as month,
                   SUM(CASE WHEN tx_type = 'credit' AND category != 'transfer' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN tx_type = 'debit' AND category != 'transfer' THEN amount ELSE 0 END) as spending,
                   SUM(CASE WHEN category = 'transfer' THEN amount ELSE 0 END) as transfers
            FROM transactions t
            WHERE 1=1 {account_filter} {date_filter}
            GROUP BY month ORDER BY month""",
        params,
    ).fetchall()

    # Category breakdown for spending (excluding transfers — they get their own card)
    category_breakdown = db.execute(
        f"""SELECT category, SUM(amount) as total
            FROM transactions t
            WHERE tx_type = 'debit' {_TRANSFER_EXCLUDE} {account_filter} {date_filter}
            GROUP BY category ORDER BY total DESC""",
        params,
    ).fetchall()

    # Account breakdown (excluding transfers)
    account_breakdown = db.execute(
        f"""SELECT a.account_name, a.institution, a.account_type,
                   SUM(CASE WHEN t.tx_type = 'credit' AND t.category != 'transfer' THEN t.amount ELSE 0 END) as income,
                   SUM(CASE WHEN t.tx_type = 'debit' AND t.category != 'transfer' THEN t.amount ELSE 0 END) as spending,
                   SUM(CASE WHEN t.category = 'transfer' THEN t.amount ELSE 0 END) as transfers
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE 1=1 {account_filter} {date_filter}
            GROUP BY a.id""",
        params,
    ).fetchall()

    recent = db.execute(
        f"""SELECT t.*, a.account_name, a.institution
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE 1=1 {account_filter} {date_filter}
            ORDER BY t.date DESC LIMIT 50""",
        params,
    ).fetchall()

    db.close()

    return {
        "total_income": total_income,
        "total_spending": total_spending,
        "net_savings": total_income - total_spending,
        "total_transfers": total_transfers,
        "monthly_trend": [dict(r) for r in monthly_trend],
        "category_breakdown": [dict(r) for r in category_breakdown],
        "account_breakdown": [dict(r) for r in account_breakdown],
        "recent_transactions": [dict(r) for r in recent],
    }


def get_weekly_breakdown(profile_id: int | None = None, year: int | None = None):
    db = get_db()
    params: list = []

    account_filter = ""
    if profile_id:
        account_filter = "AND t.account_id IN (SELECT id FROM accounts WHERE profile_id = ?)"
        params.append(profile_id)

    date_filter = ""
    if year:
        date_filter = "AND strftime('%Y', t.date) = ?"
        params.append(str(year))

    rows = db.execute(
        f"""SELECT strftime('%Y-W%W', t.date) as week,
                   SUM(CASE WHEN tx_type = 'credit' AND category != 'transfer' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN tx_type = 'debit' AND category != 'transfer' THEN amount ELSE 0 END) as spending
            FROM transactions t
            WHERE 1=1 {account_filter} {date_filter}
            GROUP BY week ORDER BY week""",
        params,
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_daily_breakdown(profile_id: int | None = None, year: int | None = None, month: int | None = None):
    db = get_db()
    params: list = []

    account_filter = ""
    if profile_id:
        account_filter = "AND t.account_id IN (SELECT id FROM accounts WHERE profile_id = ?)"
        params.append(profile_id)

    date_filter = ""
    if year and month:
        date_filter = "AND strftime('%Y', t.date) = ? AND strftime('%m', t.date) = ?"
        params.extend([str(year), f"{month:02d}"])
    elif year:
        date_filter = "AND strftime('%Y', t.date) = ?"
        params.append(str(year))

    rows = db.execute(
        f"""SELECT t.date,
                   SUM(CASE WHEN tx_type = 'credit' AND category != 'transfer' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN tx_type = 'debit' AND category != 'transfer' THEN amount ELSE 0 END) as spending
            FROM transactions t
            WHERE 1=1 {account_filter} {date_filter}
            GROUP BY t.date ORDER BY t.date""",
        params,
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_yearly_summary(profile_id: int | None = None):
    db = get_db()
    params: list = []

    account_filter = ""
    if profile_id:
        account_filter = "AND t.account_id IN (SELECT id FROM accounts WHERE profile_id = ?)"
        params.append(profile_id)

    rows = db.execute(
        f"""SELECT strftime('%Y', t.date) as year,
                   SUM(CASE WHEN tx_type = 'credit' AND category != 'transfer' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN tx_type = 'debit' AND category != 'transfer' THEN amount ELSE 0 END) as spending,
                   SUM(CASE WHEN category = 'transfer' THEN amount ELSE 0 END) as transfers
            FROM transactions t
            WHERE 1=1 {account_filter}
            GROUP BY year ORDER BY year""",
        params,
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_merchant_transactions(
    description: str,
    profile_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    tx_type: str | None = None,
):
    """Get individual transactions for a specific merchant/description."""
    db = get_db()
    params: list = [description]

    account_filter = ""
    if profile_id:
        account_filter = "AND t.account_id IN (SELECT id FROM accounts WHERE profile_id = ?)"
        params.append(profile_id)

    date_filter = ""
    if year and month:
        date_filter = "AND strftime('%Y', t.date) = ? AND strftime('%m', t.date) = ?"
        params.extend([str(year), f"{month:02d}"])
    elif year:
        date_filter = "AND strftime('%Y', t.date) = ?"
        params.append(str(year))

    type_filter = ""
    if tx_type:
        type_filter = "AND t.tx_type = ?"
        params.append(tx_type)

    rows = db.execute(
        f"""SELECT t.id, t.date, t.description, t.amount, t.tx_type, t.category, a.account_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE t.description = ? {account_filter} {date_filter} {type_filter}
            ORDER BY t.date DESC""",
        params,
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_category_breakdown_detail(
    profile_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    tx_type: str | None = None,
):
    """Get detailed breakdown: categories with their top merchants/descriptions."""
    db = get_db()
    params: list = []

    account_filter = ""
    if profile_id:
        account_filter = "AND t.account_id IN (SELECT id FROM accounts WHERE profile_id = ?)"
        params.append(profile_id)

    date_filter = ""
    if year and month:
        date_filter = "AND strftime('%Y', t.date) = ? AND strftime('%m', t.date) = ?"
        params.extend([str(year), f"{month:02d}"])
    elif year:
        date_filter = "AND strftime('%Y', t.date) = ?"
        params.append(str(year))

    type_filter = ""
    if tx_type:
        type_filter = f"AND t.tx_type = ?"
        params.append(tx_type)

    # Get category totals
    categories = db.execute(
        f"""SELECT t.category, SUM(t.amount) as total, COUNT(*) as count
            FROM transactions t
            WHERE t.category != 'transfer' {account_filter} {date_filter} {type_filter}
            GROUP BY t.category ORDER BY total DESC""",
        params,
    ).fetchall()

    result = []
    for cat_row in categories:
        cat = dict(cat_row)
        # Get top merchants/descriptions for this category
        cat_params = list(params) + [cat["category"]]
        merchants = db.execute(
            f"""SELECT t.description, SUM(t.amount) as total, COUNT(*) as count
                FROM transactions t
                WHERE t.category != 'transfer' {account_filter} {date_filter} {type_filter}
                AND t.category = ?
                GROUP BY t.description ORDER BY total DESC LIMIT 10""",
            cat_params,
        ).fetchall()
        cat["merchants"] = [dict(m) for m in merchants]
        result.append(cat)

    db.close()
    return result
