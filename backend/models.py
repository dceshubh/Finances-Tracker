from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ProfileCreate(BaseModel):
    name: str
    role: str  # 'self' or 'spouse'


class ProfileOut(BaseModel):
    id: int
    name: str
    role: str
    created_at: str


class AccountCreate(BaseModel):
    profile_id: int
    institution: str  # 'chase', 'citi', 'apple_card', 'first_tech', 'zolve'
    account_type: str  # 'checking', 'savings', 'credit_card'
    account_name: str
    last_four: Optional[str] = None


class AccountOut(BaseModel):
    id: int
    profile_id: int
    institution: str
    account_type: str
    account_name: str
    last_four: Optional[str]
    created_at: str


class StatementOut(BaseModel):
    id: int
    account_id: int
    filename: str
    file_hash: Optional[str] = None
    period_start: Optional[str]
    period_end: Optional[str]
    uploaded_at: str
    status: str
    error_message: Optional[str]


class TransactionOut(BaseModel):
    id: int
    account_id: int
    statement_id: Optional[int]
    date: str
    description: str
    amount: float
    tx_type: str
    category: str


class AnalyticsSummary(BaseModel):
    period: str
    total_income: float
    total_spending: float
    net_savings: float
    categories: dict[str, float]


class DashboardData(BaseModel):
    total_income: float
    total_spending: float
    net_savings: float
    monthly_trend: list[dict]
    category_breakdown: list[dict]
    account_breakdown: list[dict]
    recent_transactions: list[dict]
