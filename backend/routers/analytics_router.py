from fastapi import APIRouter
from ..services.analytics import (
    get_dashboard_data, get_weekly_breakdown, get_daily_breakdown,
    get_yearly_summary, get_category_breakdown_detail, get_merchant_transactions,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(profile_id: int | None = None, year: int | None = None, month: int | None = None):
    return get_dashboard_data(profile_id, year, month)


@router.get("/weekly")
def weekly(profile_id: int | None = None, year: int | None = None):
    return get_weekly_breakdown(profile_id, year)


@router.get("/daily")
def daily(profile_id: int | None = None, year: int | None = None, month: int | None = None):
    return get_daily_breakdown(profile_id, year, month)


@router.get("/yearly")
def yearly(profile_id: int | None = None):
    return get_yearly_summary(profile_id)


@router.get("/breakdown")
def breakdown(
    profile_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    tx_type: str | None = None,
):
    return get_category_breakdown_detail(profile_id, year, month, tx_type)


@router.get("/merchant-transactions")
def merchant_txns(
    description: str,
    profile_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    tx_type: str | None = None,
):
    return get_merchant_transactions(description, profile_id, year, month, tx_type)
