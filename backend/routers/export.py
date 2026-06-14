from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..services.export_service import generate_report

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/excel")
def export_excel(
    profile_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
):
    output = generate_report(profile_id, year, month)

    # Build filename
    parts = ["Finance_Report"]
    if year:
        parts.append(str(year))
    if month:
        parts.append(datetime(2000, month, 1).strftime("%B"))
    filename = "_".join(parts) + ".xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
