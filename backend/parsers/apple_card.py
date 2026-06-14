import re
import pdfplumber
from datetime import date
from .base import StatementParser, ParseResult, ParsedTransaction, ValidationTotals


# Lines to skip
_SKIP_SUBSTRINGS = [
    "total payments", "total charges", "total daily cash", "total interest",
    "date description", "payments made by", "transactions by",
    "if you have an iphone", "apple card is issued", "goldman sachs",
    "page ", "statement", "apple card customer", "daily cash for",
    "daily cash from", "total daily cash", "2026 total year",
    "interest charge", "annual percentage", "balance subject",
    "apr 1", "jan 1", "feb 1", "mar 1", "may 1", "jun 1",
    "jul 1", "aug 1", "sep 1", "oct 1", "nov 1", "dec 1",
]


class AppleCardParser(StatementParser):
    institution = "apple_card"

    def can_parse(self, text: str) -> bool:
        indicators = ["apple card", "goldman sachs", "apple cash"]
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

                validation = self._extract_validation(full_text)

                all_lines = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    all_lines.extend(text.split("\n"))

                transactions = self._parse_lines(all_lines, year)

                # Adjust year for statements spanning year boundaries
                for tx in transactions:
                    tx.date = self.adjust_tx_year(tx.date, period_start, period_end)

        except Exception as e:
            return ParseResult(error=str(e))

        return ParseResult(transactions=transactions, period_start=period_start, period_end=period_end, validation=validation)

    def _extract_year(self, text: str) -> int:
        # "Apr 1 — Apr 30, 2026" or "as of Apr 30, 2026"
        match = re.search(r",\s*(\d{4})", text)
        if match:
            yr = int(match.group(1))
            if 2020 <= yr <= 2039:
                return yr
        match = re.search(r"20[2-3]\d", text)
        return int(match.group()) if match else date.today().year

    def _extract_period(self, text: str, year: int):
        # "Apr 1 — Apr 30, 2026"
        pattern = r"(\w{3}\s+\d{1,2})\s*[—–-]\s*(\w{3}\s+\d{1,2}),?\s*(\d{4})"
        match = re.search(pattern, text)
        if match:
            start_str = match.group(1)
            end_str = f"{match.group(2)}, {match.group(3)}"
            start = self.parse_date_flexible(start_str, year)
            end = self.parse_date_flexible(end_str, year)
            if start and end:
                return start, end
        return None, None

    def _parse_lines(self, lines: list[str], year: int) -> list[ParsedTransaction]:
        txns = []
        current_section = None  # 'payments' or 'transactions'

        # Pattern for payment lines: "04/01/2026 ACH Deposit ... -$881.32"
        pat_payment = re.compile(
            r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-\$[\d,]+\.\d{2})\s*$"
        )

        # Pattern for transaction lines with daily cash:
        # "04/06/2026 AMERICAN 1 SKYVIEW DRIVE ... 2% $0.70 $35.00"
        pat_transaction = re.compile(
            r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+%)\s+\$[\d,]+\.\d{2}\s+\$?([\d,]+\.\d{2})\s*$"
        )

        # Pattern for transaction without daily cash (fallback):
        # "04/01/2026 Description $amount"
        pat_simple = re.compile(
            r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\$?[\d,]+\.\d{2})\s*$"
        )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            stripped_lower = stripped.lower()

            # Skip non-transaction lines
            if any(s in stripped_lower for s in _SKIP_SUBSTRINGS):
                continue

            # Section detection
            if stripped_lower == "payments":
                current_section = "payments"
                continue
            if stripped_lower == "transactions":
                current_section = "transactions"
                continue

            # Try payment pattern first (negative amount)
            m = pat_payment.match(stripped)
            if m:
                date_str, desc, amount_str = m.groups()
                tx_date = self.parse_date_flexible(date_str, year)
                if tx_date:
                    amount = self.clean_amount(amount_str)
                    desc = re.sub(r"\s+", " ", desc.strip())
                    txns.append(ParsedTransaction(
                        date=tx_date,
                        description=desc,
                        amount=abs(amount),
                        tx_type="credit",
                    ))
                continue

            # Try transaction with daily cash pattern
            m = pat_transaction.match(stripped)
            if m:
                date_str, desc, _pct, amount_str = m.groups()
                tx_date = self.parse_date_flexible(date_str, year)
                if tx_date:
                    amount = self.clean_amount(amount_str)
                    desc = re.sub(r"\s+", " ", desc.strip())
                    txns.append(ParsedTransaction(
                        date=tx_date,
                        description=desc,
                        amount=abs(amount),
                        tx_type="debit",
                    ))
                continue

            # Fallback simple pattern
            m = pat_simple.match(stripped)
            if m:
                date_str, desc, amount_str = m.groups()
                tx_date = self.parse_date_flexible(date_str, year)
                if tx_date:
                    amount = self.clean_amount(amount_str)
                    desc = re.sub(r"\s+", " ", desc.strip())
                    tx_type = "credit" if amount < 0 else "debit"
                    txns.append(ParsedTransaction(
                        date=tx_date,
                        description=desc,
                        amount=abs(amount),
                        tx_type=tx_type,
                    ))
                continue

        return txns

    def _extract_validation(self, text: str) -> ValidationTotals:
        """Extract expected totals from Apple Card summary (page 2).

        Apple Card's "Total charges, credits, and returns" is a NET number that
        subtracts returns and daily cash adjustments from gross charges. Since returns
        are parsed as separate credit transactions, we validate using just payments
        (which cleanly match) and skip the net charges number (which can't be directly
        compared without reconstructing daily cash adjustments).
        """
        v = ValidationTotals(source_label="Apple Card Account Activity")

        # "Total payments for this period -$850.56" — this matches cleanly
        m = re.search(r"Total payments for this period\s+-?\$?([\d,]+\.\d{2})", text)
        if m:
            v.expected_credits = self.clean_amount(m.group(1))

        # For debits, sum individual "Total charges, credits and returns" per person
        # These are net of returns but we can use gross by adding back returns.
        # However, since daily cash adjustments make exact matching impossible,
        # we use a combined validation: expected_debits = charges_net + returns = gross
        charges_net = 0.0
        m = re.search(r"Total charges, credits,? and returns for this period\s+\$?([\d,]+\.\d{2})", text)
        if m:
            charges_net = self.clean_amount(m.group(1))

        # Find returns in the text to add back (they show as "(RETURN) -$XX.XX")
        returns_total = 0.0
        for rm in re.finditer(r"\(RETURN\)\s+-?\$?([\d,]+\.\d{2})", text):
            returns_total += self.clean_amount(rm.group(1))

        if charges_net > 0:
            # expected_debits = gross charges (net + returns added back)
            # expected_credits gets returns added (payment + returns)
            v.expected_debits = charges_net + returns_total
            if v.expected_credits is not None:
                v.expected_credits += returns_total

        return v
