import re
import pdfplumber
from datetime import date
from .base import StatementParser, ParseResult, ParsedTransaction, ValidationTotals


class CitiParser(StatementParser):
    institution = "citi"

    def can_parse(self, text: str) -> bool:
        indicators = ["citibank", "citi.com", "citicards"]
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
                is_credit_card = any(kw in full_text.lower() for kw in ["credit card", "minimum payment", "new balance"])
                validation = self._extract_validation(full_text)

                for page in pdf.pages:
                    text = page.extract_text() or ""
                    transactions.extend(self._parse_page(text, year, is_credit_card))

                # Adjust year for statements spanning year boundaries
                for tx in transactions:
                    tx.date = self.adjust_tx_year(tx.date, period_start, period_end)

        except Exception as e:
            return ParseResult(error=str(e))

        return ParseResult(transactions=transactions, period_start=period_start, period_end=period_end, validation=validation)

    def _extract_year(self, text: str) -> int:
        # Try billing period date first (most reliable)
        match = re.search(r"(?:billing\s+period|statement\s+period)[:\s]*\d{2}/\d{2}/(\d{2,4})", text, re.IGNORECASE)
        if match:
            yr = match.group(1)
            return int(yr) if len(yr) == 4 else 2000 + int(yr)
        # Try "as of MM/DD/YY" pattern
        match = re.search(r"as of\s+\d{2}/\d{2}/(\d{2,4})", text, re.IGNORECASE)
        if match:
            yr = match.group(1)
            return int(yr) if len(yr) == 4 else 2000 + int(yr)
        match = re.search(r"20[2-3]\d", text)
        return int(match.group()) if match else date.today().year

    def _extract_period(self, text: str, year: int):
        pattern = r"(?:billing\s+period|statement\s+period)[:\s]*(\d{2}/\d{2}/\d{2,4})\s*(?:to|-|–)\s*(\d{2}/\d{2}/\d{2,4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return self.parse_date_flexible(match.group(1), year), self.parse_date_flexible(match.group(2), year)

        # Fallback: infer period from "Payment due date" + "MONTH STATEMENT"
        # Citi billing periods end ~25 days before the due date
        due_match = re.search(r"Payment due date[:\s]*(\d{2}/\d{2}/\d{2,4})", text, re.IGNORECASE)
        if due_match:
            from datetime import timedelta
            due_date = self.parse_date_flexible(due_match.group(1), year)
            if due_date:
                # Approximate: billing period ends ~25 days before due date
                period_end = due_date - timedelta(days=25)
                period_start = period_end - timedelta(days=30)
                return period_start, period_end

        return None, None

    def _parse_page(self, text: str, year: int, is_credit_card: bool) -> list[ParsedTransaction]:
        txns = []
        pattern = r"(\d{2}/\d{2})\s+(\d{2}/\d{2})?\s*(.+?)\s+(-?[\$]?[\d,]+\.\d{2})"
        for match in re.finditer(pattern, text):
            groups = match.groups()
            date_str = groups[0]
            desc = groups[2].strip()
            amount_str = groups[3]

            tx_date = self.parse_date_flexible(date_str, year)
            if not tx_date:
                continue

            amount = self.clean_amount(amount_str)
            desc = re.sub(r"\s+", " ", desc)

            if is_credit_card:
                tx_type = "credit" if amount < 0 else "debit"
            else:
                tx_type = "credit" if amount > 0 else "debit"
            amount = abs(amount)

            txns.append(ParsedTransaction(date=tx_date, description=desc, amount=amount, tx_type=tx_type))
        return txns

    def _extract_validation(self, text: str) -> ValidationTotals:
        """Extract expected totals from Citi statement summary."""
        v = ValidationTotals(source_label="Citi Account Summary")

        # "Purchases +$1,075.70"
        m = re.search(r"Purchases\s+\+?\$?([\d,]+\.\d{2})", text)
        if m:
            v.expected_debits = self.clean_amount(m.group(1))

        # "Payments -$969.63" + "Credits -$13.31"
        payments = 0.0
        m = re.search(r"Payments\s+-?\$?([\d,]+\.\d{2})", text)
        if m:
            payments += self.clean_amount(m.group(1))
        m = re.search(r"Credits\s+-?\$?([\d,]+\.\d{2})", text)
        if m:
            payments += self.clean_amount(m.group(1))
        if payments > 0:
            v.expected_credits = payments

        return v
