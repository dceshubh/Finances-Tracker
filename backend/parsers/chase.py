import re
import pdfplumber
from datetime import date
from .base import StatementParser, ParseResult, ParsedTransaction, ValidationTotals


# Keywords in Chase checking/savings descriptions that indicate money COMING IN
_CREDIT_KEYWORDS = [
    "deposit", "direct dep", "credit", "refund", "cashback", "cash back",
    "interest paid", "dividend", "reward", "payroll", "xfer in",
    "ach credit", "wire in",
]

# Keywords that indicate money GOING OUT
_DEBIT_KEYWORDS = [
    "debit", "withdrawal", "purchase", "pos ", "pos transaction",
    "ach debit", "bill pay", "payment", "check ", "wire out",
    "xfer out", "fee", "atm",
]

# Lines to skip in CC statements (non-transaction content)
_CC_SKIP_SUBSTRINGS = [
    "account summary", "account activity", "interest charge",
    "year-to-date", "totals year", "total fees", "total interest",
    "annual percentage", "balance type", "billing period",
    "variable rate", "daily balance", "average daily",
    "page", "statement date", "scenario-", "new balance",
    "previous balance", "payment, credits", "cash advances",
    "balance transfers", "fees charged", "interest charged",
    "credit access", "available credit", "cash access",
    "available for cash", "past due", "balance over",
    "opening/closing", "minimum payment", "payment due",
    "order number", "0000001 fis",
    # Rewards section identifiers
    "points", "rewards", "% back", "shopspot",
    "cardmembers earn", "have a question",
    "information about credit", "your account message",
    "we're glad", "so what are",
]


def _classify_checking_tx(desc: str) -> str:
    """For checking/savings statements where all amounts are positive,
    determine credit vs debit from the transaction description."""
    desc_lower = desc.lower()
    for kw in _CREDIT_KEYWORDS:
        if kw in desc_lower:
            return "credit"
    for kw in _DEBIT_KEYWORDS:
        if kw in desc_lower:
            return "debit"
    # Default: treat as debit (spending) — safer to over-count spending than under-count
    return "debit"


class ChaseParser(StatementParser):
    institution = "chase"

    # Section headers in Chase checking/savings PDFs
    _DEPOSIT_SECTIONS = [
        "deposits and additions", "deposits and other credits",
        "deposits", "other credits",
    ]
    _WITHDRAWAL_SECTIONS = [
        "electronic withdrawals", "withdrawals and other debits",
        "withdrawals", "other debits", "purchases", "fees",
        "atm & debit card withdrawals", "checks paid",
    ]

    # CC section headers — only ACCOUNT ACTIVITY sections have real transactions
    _CC_PAYMENT_SECTIONS = [
        "payments and other credits", "returns and other credits",
    ]
    _CC_PURCHASE_SECTIONS = [
        "purchase", "purchases",
    ]
    # These sections on later pages are NOT real transactions (rewards tracking, etc.)
    _CC_STOP_SECTIONS = [
        "purchases and redemptions", "interest charges", "interest charged",
        "fees", "2026 totals", "year-to-date",
    ]

    def can_parse(self, text: str) -> bool:
        indicators = ["jpmorgan chase", "chase.com", "chase bank"]
        text_lower = text.lower()
        return any(i in text_lower for i in indicators)

    def parse(self, pdf_path: str, password: str | None = None) -> ParseResult:
        transactions = []
        period_start = None
        period_end = None

        try:
            open_kw = {"password": password} if password else {}
            with pdfplumber.open(pdf_path, **open_kw) as pdf:
                full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

                year = self._extract_year(full_text)
                period_start, period_end = self._extract_period(full_text, year)

                is_credit_card = self._detect_credit_card(full_text)
                validation = self._extract_validation(full_text, is_credit_card)

                # Collect all lines across pages for continuous parsing
                all_lines = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    all_lines.extend(text.split("\n"))

                if is_credit_card:
                    transactions = self._parse_credit_card_lines(all_lines, year)
                else:
                    transactions = self._parse_checking_lines(all_lines, year)

                # Adjust year for statements spanning year boundaries (e.g., Dec-Jan)
                for tx in transactions:
                    tx.date = self.adjust_tx_year(tx.date, period_start, period_end)

        except Exception as e:
            return ParseResult(error=str(e))

        return ParseResult(transactions=transactions, period_start=period_start, period_end=period_end, validation=validation)

    def _detect_credit_card(self, text: str) -> bool:
        text_lower = text.lower()
        cc_signals = ["account number ending in", "credit card", "minimum payment due",
                      "new balance", "credit limit", "available credit", "purchase summary",
                      "account activity", "account summary"]
        checking_signals = ["checking summary", "savings summary", "beginning balance",
                           "ending balance", "deposits and additions", "electronic withdrawals",
                           "transaction detail"]
        cc_score = sum(1 for s in cc_signals if s in text_lower)
        ck_score = sum(1 for s in checking_signals if s in text_lower)
        return cc_score > ck_score

    def _extract_validation(self, text: str, is_credit_card: bool) -> ValidationTotals:
        """Extract expected totals from Chase statement summary."""
        v = ValidationTotals(source_label="Chase Account Summary")

        if is_credit_card:
            # CC: "Payment and Credits -$382.07" (or "Payment, Credits -$X")
            # "Purchase +$334.73" or "New Charges $334.73"
            m = re.search(r"(?:Payment[s]?(?:,? and| &)? Credits?)\s+-?\$?([\d,]+\.\d{2})", text, re.IGNORECASE)
            if m:
                v.expected_credits = self.clean_amount(m.group(1))
            m = re.search(r"(?:New Charges|Purchases?)\s+\+?\$?([\d,]+\.\d{2})", text, re.IGNORECASE)
            if m:
                v.expected_debits = self.clean_amount(m.group(1))
        else:
            # Checking: "Deposits and Additions $X" / "Electronic Withdrawals -$Y"
            m = re.search(r"Deposits and Additions\s+\$?([\d,]+\.\d{2})", text, re.IGNORECASE)
            if m:
                v.expected_credits = self.clean_amount(m.group(1))
            # Sum all withdrawal categories
            total_debits = 0.0
            for pat in [r"Electronic Withdrawals\s+-?\$?([\d,]+\.\d{2})",
                        r"Checks\s+-?\$?([\d,]+\.\d{2})",
                        r"ATM & Debit Card Withdrawals\s+-?\$?([\d,]+\.\d{2})",
                        r"Fees\s+-?\$?([\d,]+\.\d{2})"]:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    total_debits += self.clean_amount(m.group(1))
            if total_debits > 0:
                v.expected_debits = total_debits

        return v

    def _extract_year(self, text: str) -> int:
        # Try statement date first: "Statement Date: 05/09/26" or "Statement Date: 05/09/2026"
        m = re.search(r"Statement Date:\s*(\d{2}/\d{2}/(\d{2,4}))", text, re.IGNORECASE)
        if m:
            yr = m.group(2)
            return int(yr) if len(yr) == 4 else 2000 + int(yr)

        match = re.search(r"20[2-3]\d", text)
        return int(match.group()) if match else date.today().year

    def _extract_period(self, text: str, year: int):
        # Pattern 1: "March 24, 2026throughApril 22, 2026" (no space before "through")
        pattern1 = r"(\w+\s+\d{1,2},?\s*\d{4})\s*(?:through|to|-|–)\s*(\w+\s+\d{1,2},?\s*\d{4})"
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            start = self.parse_date_flexible(match.group(1), year)
            end = self.parse_date_flexible(match.group(2), year)
            if start and end:
                return start, end

        # Pattern 2: "Opening/Closing Date 04/10/26 - 05/09/26" (2-digit year)
        pattern2 = r"Opening/Closing Date\s+(\d{2}/\d{2}/\d{2,4})\s*-\s*(\d{2}/\d{2}/\d{2,4})"
        match = re.search(pattern2, text, re.IGNORECASE)
        if match:
            start_str, end_str = match.group(1), match.group(2)
            # Handle 2-digit year
            if len(start_str.split("/")[-1]) == 2:
                start_str = start_str[:-2] + "20" + start_str[-2:]
            if len(end_str.split("/")[-1]) == 2:
                end_str = end_str[:-2] + "20" + end_str[-2:]
            start = self.parse_date_flexible(start_str, year)
            end = self.parse_date_flexible(end_str, year)
            if start and end:
                return start, end

        # Pattern 3: full dates MM/DD/YYYY
        date_pattern = r"(\d{2}/\d{2}/\d{4})\s*(?:through|to|-|–)\s*(\d{2}/\d{2}/\d{4})"
        match = re.search(date_pattern, text)
        if match:
            start = self.parse_date_flexible(match.group(1), year)
            end = self.parse_date_flexible(match.group(2), year)
            return start, end

        return None, None

    def _parse_checking_lines(self, lines: list[str], year: int) -> list[ParsedTransaction]:
        """Parse checking/savings statement using section-aware logic.

        Chase checking format uses *start*/*end* markers AND section headers.
        Amounts are always positive; negative sign means withdrawal.
        Lines: MM/DD [MM/DD] Description Amount Balance
        """
        txns = []
        current_section = None  # 'credit' or 'debit'
        in_transaction_detail = False

        # Transaction line patterns for checking
        # Pattern A: "MM/DD MM/DD Description -Amount Balance" (two dates)
        pat_two_dates = re.compile(
            r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
        )
        # Pattern B: "MM/DD Description Amount Balance" (single date)
        pat_single_date = re.compile(
            r"^(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
        )

        for line in lines:
            stripped = line.strip()
            stripped_lower = stripped.lower()

            # Track transaction detail section
            if "*start*transaction detail" in stripped_lower:
                in_transaction_detail = True
                continue
            if "*end*transaction detail" in stripped_lower:
                in_transaction_detail = False
                continue

            if not in_transaction_detail:
                continue

            # Detect section headers within transaction detail
            if any(s in stripped_lower for s in self._DEPOSIT_SECTIONS):
                current_section = "credit"
                continue
            if any(s in stripped_lower for s in self._WITHDRAWAL_SECTIONS):
                current_section = "debit"
                continue

            # Try matching transaction lines
            m = pat_two_dates.match(stripped)
            if m:
                _tran_date, post_date, desc, amount_str, _balance = m.groups()
                date_str = post_date
            else:
                m = pat_single_date.match(stripped)
                if m:
                    date_str, desc, amount_str, _balance = m.groups()
                else:
                    continue

            tx_date = self.parse_date_flexible(date_str, year)
            if not tx_date:
                continue

            amount = self.clean_amount(amount_str)
            desc = re.sub(r"\s+", " ", desc.strip())

            # Skip summary lines (use full phrases to avoid false positives like "Card Ending IN")
            skip_phrases = ["beginning balance", "ending balance", "total ", "opening balance",
                           "closing balance", "summary", "continued"]
            if any(w in desc.lower() for w in skip_phrases):
                continue

            # Determine type: sign-based first (most reliable for Chase checking),
            # then section headers, then keyword classification as fallback
            if amount < 0:
                tx_type = "debit"
            elif amount > 0 and not current_section:
                # Positive amount with no section context = deposit/credit
                tx_type = "credit"
            elif current_section:
                tx_type = current_section
            else:
                tx_type = _classify_checking_tx(desc)

            txns.append(ParsedTransaction(
                date=tx_date,
                description=desc,
                amount=abs(amount),
                tx_type=tx_type,
            ))

        return txns

    def _parse_credit_card_lines(self, lines: list[str], year: int) -> list[ParsedTransaction]:
        """Parse credit card statement using section-aware logic.

        Chase CC format:
        - PAYMENTS AND OTHER CREDITS section: negative amounts (credits)
        - PURCHASE section: positive amounts (debits)
        - PURCHASES AND REDEMPTIONS on rewards page: skip (points, not dollars)
        - INTEREST CHARGES / FEES: skip

        Note: pdfplumber sometimes extracts doubled letters ("AACCCCOOUUNNTT") so
        we detect sections by exact header text rather than requiring "ACCOUNT ACTIVITY".
        """
        txns = []
        current_section = None  # 'credit', 'debit', or 'stop'

        # CC transaction pattern: "MM/DD Description Amount"
        pat_cc_tx = re.compile(r"^(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*$")

        for line in lines:
            stripped = line.strip()
            stripped_lower = stripped.lower()

            if not stripped or len(stripped) < 5:
                continue

            # --- Section header detection ---
            # Payment/credit sections (real transactions)
            if stripped_lower in ("payments and other credits", "payment and other credits"):
                current_section = "credit"
                continue

            # Purchase section (real transactions)
            if stripped_lower in ("purchase", "purchases"):
                current_section = "debit"
                continue

            # Stop sections — rewards tracking, interest, fees (not real transactions)
            stop_triggers = [
                "purchases and redemptions", "returns and other credits",
                "interest charges", "interest charged",
                "2026 totals", "year-to-date totals",
                "fees", "total fees", "total interest",
            ]
            if stripped_lower in stop_triggers or any(
                stripped_lower.startswith(t) for t in ["interest charge", "2026 totals", "year-to-date"]
            ):
                current_section = "stop"
                continue

            # Skip if not in a valid transaction section
            if current_section not in ("credit", "debit"):
                continue

            # Skip non-transaction lines
            if any(s in stripped_lower for s in _CC_SKIP_SUBSTRINGS):
                continue

            # Try matching transaction line
            m = pat_cc_tx.match(stripped)
            if not m:
                continue

            date_str = m.group(1)
            desc = m.group(2).strip()
            amount_str = m.group(3)

            tx_date = self.parse_date_flexible(date_str, year)
            if not tx_date:
                continue

            amount = self.clean_amount(amount_str)
            desc = re.sub(r"\s+", " ", desc)

            # Skip interest charge lines
            if "interest charge on" in desc.lower():
                continue

            # Credit card: negative = payment/refund (credit), positive = purchase (debit)
            tx_type = "credit" if amount < 0 else "debit"

            txns.append(ParsedTransaction(
                date=tx_date,
                description=desc,
                amount=abs(amount),
                tx_type=tx_type,
            ))

        return txns
