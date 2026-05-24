# backend/app/routers/data.py
"""Data endpoints for ticker search and OHLCV data retrieval."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.data_service import search_tickers, get_ohlcv

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/tickers/search")
async def search_tickers_endpoint(
    q: str = Query(..., min_length=1, description="Search query for ticker symbol or company name"),
) -> dict:
    """Search for matching stock tickers.

    Returns top 10 matching tickers from a bundled list of common US + NSE equities.
    Each result includes symbol, name, and exchange.
    """
    try:
        results = search_tickers(q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/ohlcv")
async def get_ohlcv_endpoint(
    ticker: str = Query(..., description="Stock ticker symbol"),
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> dict:
    """Get OHLCV data for a ticker and date range.

    Returns OHLCV data as a JSON array suitable for charting.
    Data is cached in PostgreSQL for performance.
    """
    if start >= end:
        raise HTTPException(
            status_code=400,
            detail={"error": "start_date must be before end_date"},
        )

    try:
        df = get_ohlcv(ticker, start, end, db)
        records = df.to_dict(orient="records")
        # Serialize dates
        for r in records:
            if hasattr(r.get("date"), "isoformat"):
                r["date"] = r["date"].isoformat()
        return {"data": records, "count": len(records)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})
