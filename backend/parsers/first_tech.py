import re
import pdfplumber
from datetime import date
from .base import StatementParser, ParseResult, ParsedTransaction, ValidationTotals


# Lines containing any of these substrings are never transactions
_SKIP_SUBSTRINGS = [
    "annual percentage yield", "dividends earned", "truth in savings",
    "p.o. box", "firsttechfed", "maturity date", "dividend rate",
    "beginning balance", "ending balance", "service charges",
    "dividends paid", "total number", "account number", "statement date",
    "page:", "billing rights", "notify us", "credit bureaus",
    "method used", "fees charged", "interest charged", "interest paid",
    "totals year", "summary loan", "payment received", "amount past due",
    "credit limit", "available funds", "due date", "annual percentage rate",
    "loan add on", "total due", "we may report", "the annual percentage",
    "there are no transactions", "this page intentionally",
    "keep this notice", "your billing rights",
]

# Regex patterns that indicate garbage (not a real transaction line)
_SKIP_PATTERNS = [
    re.compile(r"\d{3}\.\d{3}\.\d{4}"),     # phone numbers like 855.855.8805
    re.compile(r"\d+\.\d+%"),                 # percentage values like 3.50%
    re.compile(r"^\*\d+"),                     # barcode/routing lines
    re.compile(r"\(cid:\d+\)"),               # encoded characters
]

# Section headers that indicate transaction type
_DEPOSIT_HEADERS = ["deposits"]
_DEBIT_HEADERS = ["miscellaneous debits", "checks", "debits & checks"]

# Sub-account headers (to track which sub-account we're in)
_ACCOUNT_PATTERNS = [
    (re.compile(r"(FT Premier Rewards Checking|Premier Rewards Checking)\s+(\d+)", re.IGNORECASE), "checking"),
    (re.compile(r"(FT Premier Rewards Savings|Premier Rewards Savings)\s+(\d+)", re.IGNORECASE), "savings"),
    (re.compile(r"(Membership Savings)\s+(\d+)", re.IGNORECASE), "membership_savings"),
    (re.compile(r"(\d+ Month Certificate|Promo \d+ Mo.+Certificate)\s+(\d+)", re.IGNORECASE), "certificate"),
    (re.compile(r"(Personal LOC)\s", re.IGNORECASE), "loc"),
]


def _should_skip_line(line: str) -> bool:
    line_lower = line.lower().strip()
    if not line_lower or len(line_lower) < 5:
        return True
    for sub in _SKIP_SUBSTRINGS:
        if sub in line_lower:
            return True
    for pat in _SKIP_PATTERNS:
        if pat.search(line):
            return True
    return False


class FirstTechParser(StatementParser):
    institution = "first_tech"

    def can_parse(self, text: str) -> bool:
        indicators = ["first tech", "first technology", "firsttechfed", "first tech federal"]
        text_lower = text.lower()
        return any(i in text_lower for i in indicators)

    def _is_credit_card_statement(self, text: str) -> bool:
        """Detect if this is a credit card statement vs deposit/savings statement."""
        text_lower = text.lower()
        cc_signals = [
            "credit limit",
            "cash advance",
            "minimum payment due",
            "payment due date",
            "summary of account activity",
            "billing rights summary",
        ]
        return sum(1 for s in cc_signals if s in text_lower) >= 3

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

                # Parse all pages as one continuous text (sections span pages)
                all_lines = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    all_lines.extend(text.split("\n"))

                is_cc = self._is_credit_card_statement(full_text)
                validation = self._extract_validation(full_text, is_cc)

                if is_cc:
                    transactions = self._parse_cc_lines(all_lines, year)
                else:
                    transactions = self._parse_lines(all_lines, year)

                # Adjust year for statements spanning year boundaries
                for tx in transactions:
                    tx.date = self.adjust_tx_year(tx.date, period_start, period_end)

        except Exception as e:
            return ParseResult(error=str(e))

        return ParseResult(transactions=transactions, period_start=period_start, period_end=period_end, validation=validation)

    def _extract_year(self, text: str) -> int:
        # Prefer Statement Date for year (deposit statements)
        match = re.search(r"Statement Date:\s*(\d{2}/\d{2}/(\d{4}))", text)
        if match:
            return int(match.group(2))
        # Credit card statements use "Statement Closing Date MM/DD/YYYY"
        match = re.search(r"Statement Closing Date\s+(\d{2}/\d{2}/(\d{4}))", text)
        if match:
            return int(match.group(2))
        match = re.search(r"20[2-3]\d", text)
        return int(match.group()) if match else date.today().year

    def _extract_period(self, text: str, year: int):
        # Pattern 1: "For Period MM/DD through MM/DD" (no year)
        match = re.search(r"For Period\s+(\d{2}/\d{2})\s+through\s+(\d{2}/\d{2})", text, re.IGNORECASE)
        if match:
            start = self.parse_date_flexible(match.group(1), year)
            end = self.parse_date_flexible(match.group(2), year)
            if start and end:
                return start, end

        # Pattern 2: full dates with year
        pattern = r"(?:statement\s+period|period)[:\s]*(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:through|to|-|–)\s*(\d{1,2}/\d{1,2}/\d{2,4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return self.parse_date_flexible(match.group(1), year), self.parse_date_flexible(match.group(2), year)

        # Pattern 3: CC statement — use "Statement Closing Date" + "Days this Billing Cycle"
        closing_match = re.search(r"Statement Closing Date\s+(\d{2}/\d{2}/\d{4})", text)
        days_match = re.search(r"Days this Billing Cycle\s+(\d+)", text)
        if closing_match:
            from datetime import timedelta
            end = self.parse_date_flexible(closing_match.group(1), year)
            if end and days_match:
                days = int(days_match.group(1))
                start = end - timedelta(days=days - 1)
                return start, end
            return None, end

        return None, None

    def _parse_lines(self, lines: list[str], year: int) -> list[ParsedTransaction]:
        txns = []
        current_section = None       # 'credit', 'debit', or None
        current_account = None        # 'checking', 'savings', 'certificate', etc.

        # Regex for transaction lines
        # Pattern A: two-date format — "MM/DD MM/DD Description Amount"
        pat_two_dates = re.compile(
            r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*$"
        )
        # Pattern B: two-date format with trailing balance — "MM/DD MM/DD Description Amount Balance"
        pat_two_dates_bal = re.compile(
            r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})\s*$"
        )
        # Pattern C: single-date with balance — "MM/DD Description Amount Balance" (savings/cert lines)
        pat_single_date_bal = re.compile(
            r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
        )
        # Pattern D: check format — "CheckNum MM/DD Amount Trace"
        pat_check = re.compile(
            r"^(\d{1,6})\s+(\d{2}/\d{2})\s+([\d,]+\.\d{2})\s+(\d+)\s*$"
        )
        # Pattern E: savings/cert single line — "MM/DD MM/DD Description Amount Balance"
        # (already covered by pat_two_dates_bal, but we also need single-date)
        pat_single_bal = re.compile(
            r"^(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
        )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # --- Detect sub-account headers ---
            for pattern, acct_type in _ACCOUNT_PATTERNS:
                if pattern.search(stripped):
                    current_account = acct_type
                    current_section = None  # reset section when entering new account
                    break

            # --- Detect section headers ---
            stripped_lower = stripped.lower()
            if stripped_lower in ("deposits", "deposits:") or stripped_lower.startswith("deposits"):
                if "total" not in stripped_lower:
                    current_section = "credit"
                    continue
            for hdr in _DEBIT_HEADERS:
                if hdr in stripped_lower and "total" not in stripped_lower:
                    current_section = "debit"
                    break

            # "Total" lines reset section
            if stripped_lower.startswith("total "):
                current_section = None
                continue

            # --- Skip non-transaction lines ---
            if _should_skip_line(stripped):
                continue

            # --- Try to match transaction patterns ---

            # Check format: "105 01/07 2,480.00 52054030"
            m = pat_check.match(stripped)
            if m:
                check_num, date_str, amount_str, _trace = m.groups()
                tx_date = self.parse_date_flexible(date_str, year)
                if tx_date:
                    amount = self.clean_amount(amount_str)
                    txns.append(ParsedTransaction(
                        date=tx_date,
                        description=f"Check #{check_num}",
                        amount=abs(amount),
                        tx_type="debit",
                    ))
                continue

            # Two-date with balance: "01/02 01/02 ACH Debit ... -354.40"
            # Try the version with trailing balance first
            m = pat_two_dates_bal.match(stripped)
            if not m:
                m = pat_two_dates.match(stripped)
            if m:
                groups = m.groups()
                _trans_date = groups[0]
                effect_date = groups[1]
                desc = groups[2].strip()
                amount_str = groups[3]

                tx_date = self.parse_date_flexible(effect_date, year)
                if not tx_date:
                    continue

                amount = self.clean_amount(amount_str)
                desc = re.sub(r"\s+", " ", desc)

                # Skip summary lines
                if any(w in desc.lower() for w in ["starting balance", "balance", "total"]):
                    continue

                # Determine type from section or description
                if current_section:
                    tx_type = current_section
                elif amount < 0:
                    tx_type = "debit"
                elif "deposit" in desc.lower() or "credit" in desc.lower() or "dividend" in desc.lower():
                    tx_type = "credit"
                else:
                    tx_type = "debit"

                # Tag with sub-account context for non-checking accounts
                acct_label = ""
                if current_account == "savings":
                    acct_label = "[Savings] "
                elif current_account == "certificate":
                    acct_label = "[Certificate] "
                elif current_account == "membership_savings":
                    acct_label = "[Membership] "

                txns.append(ParsedTransaction(
                    date=tx_date,
                    description=f"{acct_label}{desc}" if acct_label else desc,
                    amount=abs(amount),
                    tx_type=tx_type,
                ))
                continue

            # Single-date with balance (savings/cert lines): "01/31 Credit Dividend 88.37 32,228.18"
            # or "01/31 Deposit Transfer From ******5327 2,000.00 32,139.81"
            m = pat_single_bal.match(stripped)
            if m:
                date_str, desc, amount_str, _balance = m.groups()
                tx_date = self.parse_date_flexible(date_str, year)
                if not tx_date:
                    continue

                desc = re.sub(r"\s+", " ", desc.strip())
                if any(w in desc.lower() for w in ["starting balance", "balance", "total"]):
                    continue

                amount = self.clean_amount(amount_str)

                # Savings/cert transactions are usually credits (dividends, deposits)
                if "dividend" in desc.lower() or "deposit" in desc.lower() or "credit" in desc.lower():
                    tx_type = "credit"
                elif "withdrawal" in desc.lower() or "debit" in desc.lower():
                    tx_type = "debit"
                else:
                    tx_type = "credit" if current_account in ("savings", "certificate", "membership_savings") else "debit"

                # Tag with sub-account context
                acct_label = ""
                if current_account == "savings":
                    acct_label = "[Savings] "
                elif current_account == "certificate":
                    acct_label = "[Certificate] "
                elif current_account == "membership_savings":
                    acct_label = "[Membership] "

                txns.append(ParsedTransaction(
                    date=tx_date,
                    description=f"{acct_label}{desc}",
                    amount=abs(amount),
                    tx_type=tx_type,
                ))
                continue

        return txns

    def _extract_validation(self, text: str, is_cc: bool) -> ValidationTotals:
        """Extract expected totals from First Tech statement summary."""
        v = ValidationTotals(source_label="First Tech Statement Summary")

        if is_cc:
            # CC: "+ Purchases $409.56", "- Payments $399.66"
            m = re.search(r"\+\s*Purchases\s+\$?([\d,]+\.\d{2})", text)
            if m:
                v.expected_debits = self.clean_amount(m.group(1))
            payments = 0.0
            m = re.search(r"-\s*Payments\s+\$?([\d,]+\.\d{2})", text)
            if m:
                payments += self.clean_amount(m.group(1))
            m = re.search(r"-\s*Other Credits\s+\$?([\d,]+\.\d{2})", text)
            if m:
                payments += self.clean_amount(m.group(1))
            if payments > 0:
                v.expected_credits = payments

        return v

    def _parse_cc_lines(self, lines: list[str], year: int) -> list[ParsedTransaction]:
        """Parse First Tech credit card statement lines.

        CC format: MM/DD MM/DD DESCRIPTION LOCATION REFNUMBER AMOUNT
        Negative amount = payment/credit. Positive = purchase/debit.
        """
        txns = []
        in_transactions = False
        in_interest = False

        # CC transaction line: two dates, description, ref number (alphanumeric), amount
        # Ref number is like "5543286EH5VABF41S" — alphanumeric, 15-20 chars
        pat_cc_tx = re.compile(
            r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+([A-Z0-9]{12,25})\s+(-?[\d,]+\.\d{2})\s*$"
        )
        # Fallback: some lines may not have ref number (interest charges)
        pat_cc_no_ref = re.compile(
            r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*$"
        )

        # Additional skip patterns for CC statements
        cc_skip = [
            "total fees", "total interest", "an amount preceded",
            "totals year", "type of balance", "purchases",
            "cash advances", "variable rate", "rewards",
            "points prior", "points earned", "bonus points",
            "shopspot", "points redeemed", "total points",
            "account number", "account 6523", "tran",
            "date date description", "reference",
        ]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            stripped_lower = stripped.lower()

            # Detect TRANSACTIONS section start
            if stripped_lower == "transactions":
                in_transactions = True
                in_interest = False
                continue

            # Detect FEES / INTEREST sections (skip interest charge lines with $0)
            if stripped_lower == "fees":
                in_transactions = False
                continue
            if stripped_lower == "interest charged":
                in_interest = True
                in_transactions = False
                continue

            # Stop at year-to-date / interest calculation / rewards sections
            if any(s in stripped_lower for s in ["totals year", "interest charge calculation", "rewards"]):
                in_transactions = False
                in_interest = False
                continue

            if not in_transactions and not in_interest:
                continue

            # Skip header/summary lines
            if any(s in stripped_lower for s in cc_skip):
                continue
            if _should_skip_line(stripped):
                continue

            # Try CC transaction with ref number
            m = pat_cc_tx.match(stripped)
            if m:
                _tran_date, post_date, desc, _ref, amount_str = m.groups()
                tx_date = self.parse_date_flexible(post_date, year)
                if not tx_date:
                    continue

                amount = self.clean_amount(amount_str)
                desc = re.sub(r"\s+", " ", desc.strip())

                # Negative = payment/credit, Positive = purchase/debit
                if amount < 0:
                    tx_type = "credit"
                else:
                    tx_type = "debit"

                txns.append(ParsedTransaction(
                    date=tx_date,
                    description=desc,
                    amount=abs(amount),
                    tx_type=tx_type,
                ))
                continue

            # Try without ref number (interest charge lines)
            m = pat_cc_no_ref.match(stripped)
            if m:
                _tran_date, post_date, desc, amount_str = m.groups()
                amount = self.clean_amount(amount_str)

                # Skip $0.00 interest charges
                if abs(amount) < 0.01:
                    continue

                tx_date = self.parse_date_flexible(post_date, year)
                if not tx_date:
                    continue

                desc = re.sub(r"\s+", " ", desc.strip())
                tx_type = "debit" if amount > 0 else "credit"

                txns.append(ParsedTransaction(
                    date=tx_date,
                    description=desc,
                    amount=abs(amount),
                    tx_type=tx_type,
                ))
                continue

        return txns
