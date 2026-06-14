import sqlite3
from pathlib import Path
from ..database import get_db
from ..parsers.detector import detect_and_parse, detect_account_info


def import_statement(account_id: int, pdf_path: str, institution_hint: str | None = None, password: str | None = None, file_hash: str | None = None) -> dict:
    db = get_db()

    account = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not account:
        db.close()
        return {"success": False, "error": "Account not found"}

    hint = institution_hint or account["institution"]
    detected_institution, result = detect_and_parse(pdf_path, hint, password=password)

    if result.error:
        # Don't create a failed statement record for password errors — the user will retry
        if result.error == "password_required":
            db.close()
            return {"success": False, "error": "password_required"}
        statement_id = _create_statement(db, account_id, Path(pdf_path).name, result, status="failed", file_hash=file_hash)
        db.close()
        return {"success": False, "error": result.error, "statement_id": statement_id}

    # --- Run validation ---
    validation_report = _run_validation(result)

    status = "parsed"
    if validation_report and validation_report["status"] == "mismatch":
        status = "warning"

    statement_id = _create_statement(db, account_id, Path(pdf_path).name, result, status=status, file_hash=file_hash)

    inserted = 0
    duplicates = 0
    for tx in result.transactions:
        tx_hash = tx.compute_hash(account_id)
        try:
            db.execute(
                """INSERT INTO transactions (account_id, statement_id, date, description, amount, tx_type, category, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id, statement_id, tx.date.isoformat(), tx.description, tx.amount, tx.tx_type, tx.category, tx_hash),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            duplicates += 1

    db.commit()
    db.close()

    return {
        "success": True,
        "statement_id": statement_id,
        "detected_institution": detected_institution,
        "transactions_inserted": inserted,
        "duplicates_skipped": duplicates,
        "total_parsed": len(result.transactions),
        "period_start": result.period_start.isoformat() if result.period_start else None,
        "period_end": result.period_end.isoformat() if result.period_end else None,
        "validation": validation_report,
    }


def import_statement_auto(pdf_path: str, password: str | None = None, file_hash: str | None = None) -> dict:
    """Auto-detect institution and account, then import."""
    db = get_db()

    # Step 1: Detect institution, account type, and last-4
    info = detect_account_info(pdf_path, password=password)

    if info.get("error") == "password_required":
        db.close()
        return {"success": False, "error": "password_required"}

    if not info["institution"]:
        db.close()
        return {"success": False, "error": "Could not detect bank from statement. Please set up the account and try again."}

    # Step 2: Find matching account in DB
    account_id = _match_account(db, info)

    if not account_id:
        db.close()
        inst_display = info["institution"].replace("_", " ").title()
        acct_type = (info["account_type"] or "unknown").replace("_", " ")
        last4 = info["last_four"] or "?"
        return {
            "success": False,
            "error": f"Detected {inst_display} {acct_type} (****{last4}), but no matching account found. "
                     f"Please add this account in Setup first.",
            "detected_institution": info["institution"],
            "detected_account_type": info["account_type"],
            "detected_last_four": info["last_four"],
        }

    # Step 3: Update last_four on the account if we detected it and it's missing
    if info["last_four"]:
        db.execute("UPDATE accounts SET last_four = ? WHERE id = ? AND (last_four IS NULL OR last_four = '')",
                   (info["last_four"], account_id))
        db.commit()

    # Step 4: Parse and import
    account = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    detected_institution, result = detect_and_parse(pdf_path, info["institution"], password=password)

    if result.error:
        if result.error == "password_required":
            db.close()
            return {"success": False, "error": "password_required"}
        statement_id = _create_statement(db, account_id, Path(pdf_path).name, result, status="failed", file_hash=file_hash)
        db.close()
        return {"success": False, "error": result.error, "statement_id": statement_id}

    # --- Run validation ---
    validation_report = _run_validation(result)

    status = "parsed"
    if validation_report and validation_report["status"] == "mismatch":
        status = "warning"

    statement_id = _create_statement(db, account_id, Path(pdf_path).name, result, status=status, file_hash=file_hash)

    inserted = 0
    duplicates = 0
    for tx in result.transactions:
        tx_hash = tx.compute_hash(account_id)
        try:
            db.execute(
                """INSERT INTO transactions (account_id, statement_id, date, description, amount, tx_type, category, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id, statement_id, tx.date.isoformat(), tx.description, tx.amount, tx.tx_type, tx.category, tx_hash),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            duplicates += 1

    db.commit()

    account_name = account["account_name"]
    db.close()

    return {
        "success": True,
        "statement_id": statement_id,
        "detected_institution": detected_institution,
        "detected_account": account_name,
        "detected_account_id": account_id,
        "transactions_inserted": inserted,
        "duplicates_skipped": duplicates,
        "total_parsed": len(result.transactions),
        "period_start": result.period_start.isoformat() if result.period_start else None,
        "period_end": result.period_end.isoformat() if result.period_end else None,
        "validation": validation_report,
    }


def _run_validation(result) -> dict | None:
    """Run validation comparing parsed totals against statement summary."""
    if not result.validation:
        return None

    parsed_credits = sum(t.amount for t in result.transactions if t.tx_type == "credit")
    parsed_debits = sum(t.amount for t in result.transactions if t.tx_type == "debit")
    report = result.validation.validate(parsed_credits, parsed_debits)
    report["source"] = result.validation.source_label
    report["parsed_credit_total"] = round(parsed_credits, 2)
    report["parsed_debit_total"] = round(parsed_debits, 2)
    return report


def _extract_statement_name(pdf_path: str) -> str | None:
    """Extract the primary account holder name from the first page of the PDF."""
    import re
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
            # Look for common name patterns (all-caps name after address-like context)
            # First Tech: "SHUBHAM VARSHNEY" appears as mailing name
            # Chase: "SHUBHAM VARSHNEY" in address block
            # Try to find a name that matches a known profile
            return text
    except Exception:
        return None


def _match_account(db, info: dict) -> int | None:
    """Find the best matching account in DB for detected statement info.

    Matching priority:
    1. institution + account_type + last_four (exact match)
    2. institution + account_type + card_variant (name-based match for Chase etc.)
    3. institution + account_type (if only one account matches)
    """
    institution = info["institution"]
    account_type = info["account_type"]
    last_four = info["last_four"]
    card_variant = info.get("card_variant")

    # Priority 1: Full match with last_four
    if last_four:
        row = db.execute(
            "SELECT id FROM accounts WHERE institution = ? AND account_type = ? AND last_four = ?",
            (institution, account_type, last_four)
        ).fetchone()
        if row:
            return row["id"]

    # Priority 2: Card variant name matching (e.g., "amazon" matches "Chase Amazon Prime")
    if card_variant:
        candidates = db.execute(
            "SELECT id, account_name FROM accounts WHERE institution = ? AND account_type = ?",
            (institution, account_type)
        ).fetchall()
        for c in candidates:
            if card_variant.lower() in c["account_name"].lower():
                return c["id"]

    # Priority 3: institution + account_type — only if there's exactly one match
    candidates = db.execute(
        "SELECT a.id, a.account_name, p.name as profile_name FROM accounts a "
        "JOIN profiles p ON a.profile_id = p.id "
        "WHERE a.institution = ? AND a.account_type = ?",
        (institution, account_type)
    ).fetchall()
    if len(candidates) == 1:
        return candidates[0]["id"]

    # Priority 4: Multiple matches — try to disambiguate by profile name in PDF text
    if len(candidates) > 1:
        pdf_text = info.get("_pdf_text", "").lower()
        if pdf_text:
            for c in candidates:
                profile_name = c["profile_name"].lower()
                # Check if the profile's name appears in the PDF
                name_parts = profile_name.split()
                if all(part in pdf_text for part in name_parts):
                    return c["id"]

    # Priority 5: If last_four detected but no exact type match, try across all types
    if last_four:
        row = db.execute(
            "SELECT id FROM accounts WHERE institution = ? AND last_four = ?",
            (institution, last_four)
        ).fetchone()
        if row:
            return row["id"]

    return None


def _create_statement(db, account_id, filename, result, status, file_hash=None):
    cursor = db.execute(
        """INSERT INTO statements (account_id, filename, file_hash, period_start, period_end, status, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            account_id,
            filename,
            file_hash,
            result.period_start.isoformat() if result.period_start else None,
            result.period_end.isoformat() if result.period_end else None,
            status,
            result.error,
        ),
    )
    db.commit()
    return cursor.lastrowid
