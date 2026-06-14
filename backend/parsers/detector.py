import re
import pdfplumber
from .base import ParseResult
from .chase import ChaseParser
from .citi import CitiParser
from .apple_card import AppleCardParser
from .first_tech import FirstTechParser
from .zolve import ZolveParser

ALL_PARSERS = [ChaseParser(), CitiParser(), AppleCardParser(), FirstTechParser(), ZolveParser()]


# Primary institution indicators — these appear in headers/branding, not payment descriptions.
# Scored: count matches, highest score wins. This avoids false matches from transaction text.
_INSTITUTION_SIGNALS = {
    "chase": [
        ("jpmorgan chase", 5), ("chase.com", 3), ("chase bank", 4),
        ("chase mobile", 2), ("chase credit", 2),
    ],
    "citi": [
        ("citicards.com", 5), ("citibank", 4), ("citi cards", 3),
        ("costco anywhere visa", 3),
    ],
    "apple_card": [
        ("apple card", 5), ("goldman sachs bank", 4), ("card.apple.com", 4),
        ("daily cash", 2),
    ],
    "first_tech": [
        ("first tech federal credit union", 6), ("firsttechfed.com", 5),
        ("firsttechfed", 4), ("first technology", 3),
    ],
    "zolve": [
        ("zolve.com", 5), ("zolve innovations", 5), ("zolve credit", 4),
        ("hello@zolve.com", 4),
    ],
}


def detect_and_parse(pdf_path: str, institution_hint: str | None = None, password: str | None = None) -> tuple[str, ParseResult]:
    if institution_hint:
        for parser in ALL_PARSERS:
            if parser.institution == institution_hint:
                return parser.institution, parser.parse(pdf_path, password=password)

    open_kw = {"password": password} if password else {}
    try:
        with pdfplumber.open(pdf_path, **open_kw) as pdf:
            sample_text = "\n".join(p.extract_text() or "" for p in pdf.pages[:2])
    except Exception as e:
        err_name = type(e).__name__
        if "password" in err_name.lower() or "encrypt" in str(e).lower():
            return "unknown", ParseResult(error="password_required")
        return "unknown", ParseResult(error=f"Failed to read PDF: {e}")

    for parser in ALL_PARSERS:
        if parser.can_parse(sample_text):
            return parser.institution, parser.parse(pdf_path, password=password)

    return "unknown", ParseResult(error="Could not detect bank. Please select the institution manually.")


def _detect_card_variant(text_lower: str, institution: str) -> str | None:
    """Detect specific card variant for institutions with multiple credit cards.
    Returns a keyword that can match against account_name in the DB."""
    if institution == "chase":
        if "prime visa" in text_lower or "amazon" in text_lower and "chase.com/amazon" in text_lower:
            return "amazon"
        if "sapphire" in text_lower or "ultimate rewards" in text_lower:
            return "sapphire"
        if "freedom" in text_lower:
            return "freedom"
    return None


def detect_account_info(pdf_path: str, password: str | None = None) -> dict:
    """Auto-detect institution, account type, and last-4 digits from a PDF statement.

    Returns dict with keys:
        institution: str | None
        account_type: 'checking' | 'savings' | 'credit_card' | None
        last_four: str | None  (4-digit string)
        confidence: 'high' | 'medium' | 'low'
    """
    try:
        open_kw = {"password": password} if password else {}
        with pdfplumber.open(pdf_path, **open_kw) as pdf:
            sample_text = "\n".join(p.extract_text() or "" for p in pdf.pages[:3])
    except Exception as e:
        err_name = type(e).__name__
        if "password" in err_name.lower() or "encrypt" in str(e).lower():
            return {"institution": None, "account_type": None, "last_four": None, "card_variant": None,
                    "confidence": "low", "error": "password_required"}
        return {"institution": None, "account_type": None, "last_four": None, "confidence": "low"}

    text_lower = sample_text.lower()

    # --- Detect institution using scored signals ---
    scores: dict[str, int] = {}
    for inst, signals in _INSTITUTION_SIGNALS.items():
        score = sum(weight for keyword, weight in signals if keyword in text_lower)
        if score > 0:
            scores[inst] = score

    if not scores:
        # Fallback to can_parse()
        for parser in ALL_PARSERS:
            if parser.can_parse(sample_text):
                scores[parser.institution] = 1
                break

    if not scores:
        return {"institution": None, "account_type": None, "last_four": None, "card_variant": None, "confidence": "low"}

    institution = max(scores, key=scores.get)  # type: ignore

    # --- Detect account type ---
    account_type = _detect_account_type(text_lower, institution)

    # --- Detect last-4 digits ---
    last_four = _detect_last_four(sample_text, institution)

    # --- Detect card variant (for disambiguation) ---
    card_variant = _detect_card_variant(text_lower, institution)

    confidence = "high" if institution and account_type and (last_four or card_variant) else "medium" if institution and account_type else "low"

    return {
        "institution": institution,
        "account_type": account_type,
        "last_four": last_four,
        "card_variant": card_variant,
        "confidence": confidence,
        "_pdf_text": sample_text,  # used internally for profile name matching
    }


def _detect_account_type(text_lower: str, institution: str) -> str | None:
    """Determine if statement is checking, savings, or credit card."""

    # Strong credit card signals
    cc_signals = [
        "credit card", "minimum payment", "credit limit", "available credit",
        "purchases", "cash advance", "payment due date", "new balance",
        "billing period", "bill period", "interest charged",
        "annual percentage rate (apr)", "mastercard", "visa card",
    ]
    cc_score = sum(1 for s in cc_signals if s in text_lower)

    # Strong checking/savings signals
    check_signals = [
        "checking", "deposits", "miscellaneous debits", "checks",
        "beginning balance", "ending balance", "direct deposit",
        "for period", "debits & checks",
    ]
    check_score = sum(1 for s in check_signals if s in text_lower)

    savings_signals = [
        "savings", "certificate", "dividend rate", "maturity date",
        "membership savings",
    ]
    savings_score = sum(1 for s in savings_signals if s in text_lower)

    if cc_score >= 3:
        return "credit_card"
    if savings_score > check_score and savings_score >= 2:
        return "savings"
    if check_score >= 2:
        return "checking"

    # Institution-specific defaults
    if institution == "apple_card":
        return "credit_card"
    if institution == "zolve":
        return "credit_card"

    return "credit_card" if cc_score > check_score else "checking" if check_score > 0 else None


def _detect_last_four(text: str, institution: str) -> str | None:
    """Extract last 4 digits of the statement's own account number.

    Uses institution-specific patterns to avoid grabbing payment
    destination account numbers (e.g., "payment from account ending 0018"
    is the source bank, not this card's number).
    """

    if institution == "chase":
        # Chase: "Account Number: ...1044" or "Account ending in 1044"
        m = re.search(r"Account\s+Number:\s*\S*?(\d{4})\b", text)
        if m:
            return m.group(1)
        m = re.search(r"account\s+ending\s+in\s+(\d{4})", text, re.IGNORECASE)
        if m:
            return m.group(1)

    elif institution == "citi":
        # Citi: "Account number ending in: 6235"
        m = re.search(r"account\s+number\s+ending\s+in[:\s]*(\d{4})", text, re.IGNORECASE)
        if m:
            return m.group(1)

    elif institution == "first_tech":
        # First Tech: "Account Number Ending In 5009" or "Account Number 5261 0200 2585 5009"
        m = re.search(r"Account\s+Number\s+Ending\s+In\s+(\d{4})", text, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"Account\s+Number[:\s]+(?:\d{4}\s+)*(\d{4})\b", text)
        if m:
            return m.group(1)
        # Checking: "Account Number: 9343720018" → last 4 (skip if all zeros)
        m = re.search(r"Account\s+Number:\s*(\d+)", text)
        if m:
            last4 = m.group(1)[-4:]
            if last4 != "0000":
                return last4

    elif institution == "zolve":
        # Zolve: "Card Ending in - * 5141" or "Card Ending in *5141"
        m = re.search(r"Card\s+Ending\s+in\s*[-*\s]*(\d{4})", text, re.IGNORECASE)
        if m:
            return m.group(1)

    elif institution == "apple_card":
        # Apple Card doesn't show a card number on the statement.
        # The "account ending in XXXX" references are for *payment source* accounts.
        return None

    # Generic fallback (less reliable)
    # Only match "Account Number Ending In XXXX" style (not "account ending XXXX" which could be payment source)
    m = re.search(r"Account\s+Number\s+Ending\s+In[:\s]*(\d{4})", text, re.IGNORECASE)
    if m:
        return m.group(1)

    return None
