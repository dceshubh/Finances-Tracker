from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import hashlib
import re


CATEGORY_KEYWORDS = {
    "groceries": ["grocery", "whole foods", "wholefds", "trader joe", "safeway", "kroger",
                   "walmart supercenter", "wm supercenter", "costco", "target", "aldi", "sprouts", "hmart",
                   "fred meyer", "fred-meyer", "winco", "publix", "wegmans", "food lion", "piggly",
                   "stop & shop", "india metro", "indian grocery", "patel brothers",
                   "apna bazaar", "apna bazar", "dk market", "dollar tree", "dollartree",
                   "mayuri foods", "all india spice"],
    "dining": ["restaurant", "doordash", "uber eats", "grubhub", "mcdonald", "starbucks", "chipotle",
               "subway", "pizza", "taco bell", "wendy", "chick-fil-a", "panda express", "cafe",
               "dunkin", "panera", "buffalo wild", "ihop", "denny", "waffle", "sushi", "thai",
               "chinese", "indian", "burrito", "noodle", "ramen", "bakery",
               "boba ", "boba up", "desi adda", "chaat house", "bombay", "honestbellevue",
               "canteen vending", "zaika", "dilli-6", "dilli 6", "taste of nepal",
               "desi bite", "masthi", "inchin", "timeless tea", "dominos", "domino's",
               "papa john", "cheesecake", "cloves"],
    "gas": ["shell", "chevron", "exxon", "bp ", "arco", "gas station", "fuel", "7-eleven fuel",
            "costco gas", "costco gas #", "speedway", "circle k", "pilot"],
    "transportation": ["uber ", "lyft", "transit", "parking", "toll", "metro transit", "taxi", "cab ",
                       "king county metro", "sound transit", "orca", "paybyphone", "parkwhiz",
                       "goodtogo", "wsdot", "uw pay"],
    "auto": ["auto loan", "car loan", "nissan", "toyota", "honda", "ford motor", "car payment",
             "vehicle", "dmv", "registration", "smog", "car wash", "jiffy lube", "autozone",
             "o'reilly", "tire", "mechanic", "nissan ret"],
    "utilities": ["electric", "water", "sewage", "garbage", "internet", "comcast", "xfinity",
                  "at&t", "att ", "t-mobile", "verizon", "vzwrlss", "vzw", "pg&e", "utility",
                  "spectrum", "cox comm", "centurylink", "frontier comm", "energy",
                  "power", "gas bill", "phone bill"],
    "rent": ["rent ", "rent/", "lease", "apartment", "property mgmt", "mortgage", "housing",
             "check #"],
    "insurance": ["insurance", "geico", "progressive", "state farm", "allstate", "liberty mutual",
                  "usaa", "farmers", "nationwide", "metlife", "prudential"],
    "healthcare": ["pharmacy", "cvs", "walgreens", "doctor", "hospital", "dental", "medical",
                   "health", "kaiser", "clinic", "optometry", "vision", "lab ", "quest diag",
                   "labcorp", "urgent care", "copay", "natera", "otf ", "orangetheory"],
    "shopping": ["amazon", "walmart", "wal-mart", "target", "best buy", "apple.com", "nike",
                 "home depot", "lowes", "ikea", "nordstrom", "ross", "marshall", "tj maxx",
                 "costco", "ebay", "etsy", "wayfair", "pottery barn", "crate & barrel",
                 "bed bath", "amazon.com svcs", "great clips", "carters", "carter's",
                 "columbia ", "tommy hilfiger", "bella botega", "cox store"],
    "subscriptions": ["netflix", "spotify", "hulu", "disney+", "youtube", "apple music", "hbo",
                      "prime video", "audible", "openai", "anthropic", "claude.ai", "adobe",
                      "microsoft 365", "google storage", "icloud", "dropbox", "paramount",
                      "peacock", "zoom management", "fansly", "apple.com/bill", "sling tv"],
    "travel": ["airline", "hotel", "airbnb", "booking.com", "expedia", "southwest", "delta",
               "united", "american air", "american 1 skyview", "marriott", "hilton", "hyatt",
               "frontier air", "spirit", "jetblue", "alaska air", "vrbo", "chase travel",
               "tripchrg", "sevencorners", "travel insurance", "lemonade insurance"],
    "education": ["tuition", "university", "college", "coursera", "udemy", "school", "student loan",
                  "education", "textbook", "chegg", "interviewready"],
    "entertainment": ["movie", "theater", "concert", "ticket", "amc", "regal", "spotify",
                      "gaming", "steam", "playstation", "xbox", "nintendo",
                      "gym", "fitness", "planet fitness", "la fitness",
                      "24 hour fitness", "equinox", "crunch", "roozengaarde",
                      "space needle"],
    "investments": ["brokerage", "raymond james", "fidelity", "fid bkg svc", "schwab", "vanguard",
                    "etrade", "robinhood", "wealthfront", "betterment", "merrill", "td ameritrade",
                    "investment", "stock", "401k", "ira ", "moneyline"],
    "transfer": ["transfer", "zelle", "venmo", "paypal", "wire", "xfer", "ach credit",
                 "external transfer", "olb external", "bank to ca", "zolved", "zolve innovation",
                 "banktocard",
                 # Credit card payment lines (checking side — debits)
                 "citi card online", "chase credit crd", "epay", "card payment",
                 "credit card payment", "apple card", "discover payment",
                 "payment to chase card", "payment to citi", "apple cash bank xfer",
                 "ach payment from",
                 # Credit card payment lines (CC side — credits)
                 "payment thank you", "payment received", "autopay payment",
                 "payment - thank", "online payment",
                 # Inter-account transfers
                 "deposit transfer from", "withdrawal varshney pmt",
                 # Certificate maturity (principal movement, not real income/spending)
                 "closeout withdrawal", "closeout deposit", "descriptive deposit",
                 # External transfers (self-to-self across banks)
                 "first tech fcu extrnltfr", "wise inc", "wise trnwise"],
    "income": ["payroll", "direct dep", "salary", "wage", "interest paid", "dividend",
               "refund", "cashback", "cash back", "reward", "credit dividend",
               "annual percentage yield", "apy", "irs treas", "tax ref"],
    "fees": ["fee", "service charge", "overdraft", "nsf", "monthly maintenance",
             "atm fee", "foreign transaction", "best tax filer"],
}


# Categories checked first — these contain keywords that overlap with lower-priority
# categories (e.g., "amazon" appears in shopping, but "payroll" in income should win).
_HIGH_PRIORITY_CATEGORIES = ["income", "transfer", "fees"]


def categorize(description: str) -> str:
    desc_lower = description.lower()

    # Check high-priority categories first
    for cat in _HIGH_PRIORITY_CATEGORIES:
        if cat in CATEGORY_KEYWORDS:
            for kw in CATEGORY_KEYWORDS[cat]:
                if kw in desc_lower:
                    return cat

    # Specific compound keyword overrides (resolve ambiguities before general matching)
    # e.g., "costco gas" → gas, not groceries; "amazon pharmacy" → healthcare, not shopping
    _COMPOUND_OVERRIDES = [
        ("costco gas", "gas"),
        ("amazon pharmacy", "healthcare"),
        ("apple.com/bill", "subscriptions"),
        ("wholefds", "groceries"),
        ("wal-mart #", "shopping"),  # Regular walmart → shopping (groceries use "wm supercenter")
    ]
    for compound_kw, cat in _COMPOUND_OVERRIDES:
        if compound_kw in desc_lower:
            return cat

    # Then check the rest in insertion order
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category in _HIGH_PRIORITY_CATEGORIES:
            continue  # already checked
        for kw in keywords:
            if kw in desc_lower:
                return category
    return "other"


@dataclass
class ParsedTransaction:
    date: date
    description: str
    amount: float
    tx_type: str  # 'credit' or 'debit'
    category: str = ""

    def __post_init__(self):
        if not self.category:
            self.category = categorize(self.description)

    def compute_hash(self, account_id: int) -> str:
        raw = f"{account_id}|{self.date.isoformat()}|{self.description.strip()}|{self.amount:.2f}|{self.tx_type}"
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class ValidationTotals:
    """Expected totals extracted from the statement summary for cross-checking."""
    expected_credits: Optional[float] = None   # payments, deposits, credits
    expected_debits: Optional[float] = None    # purchases, withdrawals, debits
    source_label: str = ""                     # e.g., "Statement Summary" — where the totals came from

    def validate(self, parsed_credits: float, parsed_debits: float) -> dict:
        """Compare parsed totals against expected. Returns validation report.

        Tolerance: allows $2 absolute OR 0.5% relative difference to handle
        Daily Cash Adjustments and rounding in Apple Card statements.
        """
        result = {"status": "ok", "checks": []}

        def _is_match(parsed: float, expected: float) -> bool:
            diff = abs(parsed - expected)
            # $2 absolute tolerance OR 0.5% of expected
            return diff < 2.00 or (expected > 0 and diff / expected < 0.005)

        if self.expected_credits is not None:
            ok = _is_match(parsed_credits, self.expected_credits)
            result["checks"].append({
                "label": "Credits/Payments",
                "expected": self.expected_credits,
                "parsed": parsed_credits,
                "match": ok,
            })
            if not ok:
                result["status"] = "mismatch"

        if self.expected_debits is not None:
            ok = _is_match(parsed_debits, self.expected_debits)
            result["checks"].append({
                "label": "Debits/Purchases",
                "expected": self.expected_debits,
                "parsed": parsed_debits,
                "match": ok,
            })
            if not ok:
                result["status"] = "mismatch"

        if not result["checks"]:
            result["status"] = "no_validation"

        return result


@dataclass
class ParseResult:
    transactions: list[ParsedTransaction] = field(default_factory=list)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    error: Optional[str] = None
    validation: Optional[ValidationTotals] = None
    detected_account_hint: Optional[str] = None   # e.g., "credit_card:5009" for auto-detect


class StatementParser:
    institution: str = "generic"

    def can_parse(self, text: str) -> bool:
        raise NotImplementedError

    def parse(self, pdf_path: str, password: str | None = None) -> ParseResult:
        raise NotImplementedError

    @staticmethod
    def clean_amount(amount_str: str) -> float:
        cleaned = re.sub(r"[^\d.\-]", "", amount_str.replace(",", ""))
        return float(cleaned) if cleaned else 0.0

    @staticmethod
    def parse_date_flexible(date_str: str, year: Optional[int] = None) -> Optional[date]:
        import re
        from datetime import datetime

        date_str = date_str.strip()
        formats = [
            "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y",
            "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d",
            "%m/%d", "%b %d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.year == 1900 and year:
                    dt = dt.replace(year=year)
                return dt.date()
            except ValueError:
                continue
        return None

    @staticmethod
    def adjust_tx_year(tx_date: date, period_start: Optional[date], period_end: Optional[date]) -> date:
        """Adjust transaction date year for statements spanning year boundaries.

        CC statements often span Dec-Jan. A transaction dated 12/27 in a statement
        for period 12/24/2025 - 01/23/2026 should be 2025-12-27, not 2026-12-27.
        """
        if not period_start and not period_end:
            return tx_date

        # If we have both start and end, check if tx_date falls unreasonably far
        # from the period. If tx month is > 6 months after period_end, it's likely
        # from the prior year.
        if period_end:
            from datetime import timedelta
            # If tx_date is more than 60 days after period_end, try prior year
            if tx_date > period_end + timedelta(days=60):
                adjusted = tx_date.replace(year=tx_date.year - 1)
                # Verify the adjusted date is reasonable (within or near the period)
                if period_start and adjusted >= period_start - timedelta(days=5):
                    return adjusted
                elif not period_start:
                    return adjusted

        if period_start:
            from datetime import timedelta
            # If tx_date is more than 60 days before period_start, try next year
            if tx_date < period_start - timedelta(days=60):
                adjusted = tx_date.replace(year=tx_date.year + 1)
                if period_end and adjusted <= period_end + timedelta(days=5):
                    return adjusted

        return tx_date
