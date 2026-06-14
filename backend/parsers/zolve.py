import re
import pdfplumber
from datetime import date
from .base import StatementParser, ParseResult, ParsedTransaction, ValidationTotals


class ZolveParser(StatementParser):
    institution = "zolve"

    def can_parse(self, text: str) -> bool:
        indicators = ["zolve", "zolve.com"]
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

                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        transactions.extend(self._parse_tables(tables, year))

                # Adjust year for statements spanning year boundaries
                for tx in transactions:
                    tx.date = self.adjust_tx_year(tx.date, period_start, period_end)

        except Exception as e:
            return ParseResult(error=str(e))

        return ParseResult(transactions=transactions, period_start=period_start, period_end=period_end, validation=validation)

    def _extract_year(self, text: str) -> int:
        # Try bill period date first
        match = re.search(r"Bill Period:\s*\d{2}/\d{2}/(\d{4})", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"Statement Date\s+\d{2}/\d{2}/(\d{4})", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"20[2-3]\d", text)
        return int(match.group()) if match else date.today().year

    def _extract_period(self, text: str, year: int):
        # "Bill Period: 03/15/2026 - 04/14/2026"
        pattern = r"Bill Period:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return self.parse_date_flexible(match.group(1), year), self.parse_date_flexible(match.group(2), year)

        # Fallback: "Billing Period: ..."
        pattern2 = r"(?:billing\s+period|statement\s+period)[:\s]*(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:to|-|–)\s*(\d{1,2}/\d{1,2}/\d{2,4})"
        match = re.search(pattern2, text, re.IGNORECASE)
        if match:
            return self.parse_date_flexible(match.group(1), year), self.parse_date_flexible(match.group(2), year)

        return None, None

    def _parse_tables(self, tables: list, year: int) -> list[ParsedTransaction]:
        """Parse Zolve CC statement tables.

        Table structure:
        - Row with "Payments and Other Credits" → credit section
        - Row with "Purchases and Cash Advances" → debit section
        - Row with "Fees Charged" / "Interest Charged" → stop
        - Transaction rows: [PostedDate, TransactionDate, Description, Amount]
        """
        txns = []
        current_section = None  # 'credit' or 'debit'

        for table in tables:
            for row in table:
                if not row or len(row) < 1:
                    continue

                first_cell = (row[0] or "").strip().lower()

                # Section detection
                if "payments" in first_cell and "credits" in first_cell:
                    current_section = "credit"
                    continue
                if "purchases" in first_cell:
                    current_section = "debit"
                    continue
                if first_cell.startswith("fees charged") or first_cell.startswith("interest charged"):
                    current_section = None
                    continue

                # Skip non-transaction rows
                if not current_section:
                    continue
                if len(row) < 4:
                    continue
                if first_cell.startswith("sub total") or first_cell.startswith("posted date"):
                    continue
                if first_cell.startswith("no transaction"):
                    continue
                if not first_cell:
                    continue

                posted_date = (row[0] or "").strip()
                _tran_date = (row[1] or "").strip()
                desc = (row[2] or "").strip()
                amount_str = (row[3] or "").strip()

                # Validate date format
                if not re.match(r"\d{2}/\d{2}/\d{4}", posted_date):
                    continue

                tx_date = self.parse_date_flexible(posted_date, year)
                if not tx_date:
                    continue

                # Clean description (may have newlines from wrapped text)
                desc = re.sub(r"\s+", " ", desc)
                if not desc:
                    continue

                amount = self.clean_amount(amount_str)
                if abs(amount) < 0.01:
                    continue

                # Type from section (amounts are always positive in Zolve)
                tx_type = current_section

                txns.append(ParsedTransaction(
                    date=tx_date,
                    description=desc,
                    amount=abs(amount),
                    tx_type=tx_type,
                ))

        return txns

    def _extract_validation(self, text: str) -> ValidationTotals:
        """Extract expected totals from Zolve statement summary."""
        v = ValidationTotals(source_label="Zolve Account Summary")

        # "Purchases $147.00"
        m = re.search(r"Purchases\s+\$?([\d,]+\.\d{2})", text)
        if m:
            v.expected_debits = self.clean_amount(m.group(1))

        # "Payments $60.59"
        payments = 0.0
        m = re.search(r"Payments\s+\$?([\d,]+\.\d{2})", text)
        if m:
            payments += self.clean_amount(m.group(1))
        m = re.search(r"Other Credits\s+\$?([\d,]+\.\d{2})", text)
        if m:
            payments += self.clean_amount(m.group(1))
        if payments > 0:
            v.expected_credits = payments

        return v
