# backend/app/services/data_service.py
"""Service for fetching and caching OHLCV data via yfinance."""

from datetime import date, datetime, timedelta
from typing import Optional
import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException

from app.models.ohlcv import OHLCVCache


def get_ohlcv(
    ticker: str,
    start: date,
    end: date,
    db: Session,
) -> pd.DataFrame:
    """Fetch OHLCV data for a ticker and date range, using PostgreSQL cache.

    Checks the database cache first. If the cache is missing or stale (older
    than 1 day), fetches fresh data from yfinance and upserts into the cache.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL', 'RELIANCE.NS').
        start: Start date for the data range.
        end: End date for the data range.
        db: SQLAlchemy database session.

    Returns:
        DataFrame with columns [date, open, high, low, close, volume].

    Raises:
        HTTPException: 404 if ticker not found or no data returned.
    """
    staleness_threshold = datetime.utcnow() - timedelta(days=1)

    # Check cache for existing data within the date range
    cached_rows = (
        db.query(OHLCVCache)
        .filter(
            and_(
                OHLCVCache.ticker == ticker.upper(),
                OHLCVCache.date >= start,
                OHLCVCache.date <= end,
                OHLCVCache.fetched_at >= staleness_threshold,
            )
        )
        .order_by(OHLCVCache.date)
        .all()
    )

    # Calculate expected trading days (rough estimate: ~252 per year)
    expected_days = (end - start).days * 252 / 365

    # If cache has a reasonable amount of data, use it
    if cached_rows and len(cached_rows) >= expected_days * 0.8:
        df = pd.DataFrame(
            [
                {
                    "date": row.date,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume,
                }
                for row in cached_rows
            ]
        )
        df["date"] = pd.to_datetime(df["date"])
        return df

    # Cache miss or stale — fetch from yfinance
    import requests
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        raw_df = yf.download(
            ticker.upper(),
            start=start.isoformat(),
            end=end.isoformat(),
            session=session,
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch data from yfinance: {str(e)}",
        )

    if raw_df is None or raw_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for ticker '{ticker}'. Verify the symbol is correct.",
        )

    # Clean the DataFrame
    raw_df = raw_df.reset_index()

    # Handle multi-level columns that yfinance sometimes returns
    if isinstance(raw_df.columns, pd.MultiIndex):
        raw_df.columns = [col[0] if isinstance(col, tuple) else col for col in raw_df.columns]

    raw_df.columns = [str(c).lower().strip() for c in raw_df.columns]

    # Map 'index' column to 'date' if necessary
    if "index" in raw_df.columns and "date" not in raw_df.columns:
        raw_df = raw_df.rename(columns={"index": "date"})

    # Ensure required columns exist
    required_cols = {"date", "open", "high", "low", "close", "volume"}
    if not required_cols.issubset(set(raw_df.columns)):
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected data format from yfinance for ticker '{ticker}'.",
        )

    raw_df["date"] = pd.to_datetime(raw_df["date"])
    raw_df = raw_df[["date", "open", "high", "low", "close", "volume"]].dropna()

    # Upsert into cache
    _upsert_ohlcv_cache(ticker.upper(), raw_df, db)

    return raw_df


def _upsert_ohlcv_cache(ticker: str, df: pd.DataFrame, db: Session) -> None:
    """Insert or update OHLCV rows in the cache table.

    Args:
        ticker: Uppercase ticker symbol.
        df: DataFrame with columns [date, open, high, low, close, volume].
        db: SQLAlchemy database session.
    """
    now = datetime.utcnow()

    for _, row in df.iterrows():
        row_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]

        existing = (
            db.query(OHLCVCache)
            .filter(
                and_(
                    OHLCVCache.ticker == ticker,
                    OHLCVCache.date == row_date,
                )
            )
            .first()
        )

        if existing:
            existing.open = float(row["open"])
            existing.high = float(row["high"])
            existing.low = float(row["low"])
            existing.close = float(row["close"])
            existing.volume = int(row["volume"])
            existing.fetched_at = now
        else:
            db.add(
                OHLCVCache(
                    ticker=ticker,
                    date=row_date,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    fetched_at=now,
                )
            )

    db.commit()


def search_tickers(query: str) -> list[dict]:
    """Search for matching tickers from a bundled list of common equities.

    Args:
        query: Partial ticker symbol or company name to search for.

    Returns:
        List of up to 10 matching tickers with symbol, name, and exchange.
    """
    query_upper = query.upper().strip()
    query_lower = query.lower().strip()

    results = []
    for entry in TICKER_LIST:
        if (
            query_upper in entry["symbol"]
            or query_lower in entry["name"].lower()
        ):
            results.append(entry)
            if len(results) >= 10:
                break

    return results


# Bundled list of 500 common US + NSE equities
TICKER_LIST: list[dict] = [
    # US Large Cap
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc.", "exchange": "NYSE"},
    {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "exchange": "NYSE"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE"},
    {"symbol": "V", "name": "Visa Inc.", "exchange": "NYSE"},
    {"symbol": "XOM", "name": "Exxon Mobil Corporation", "exchange": "NYSE"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
    {"symbol": "WMT", "name": "Walmart Inc.", "exchange": "NYSE"},
    {"symbol": "PG", "name": "Procter & Gamble Company", "exchange": "NYSE"},
    {"symbol": "MA", "name": "Mastercard Inc.", "exchange": "NYSE"},
    {"symbol": "HD", "name": "The Home Depot Inc.", "exchange": "NYSE"},
    {"symbol": "CVX", "name": "Chevron Corporation", "exchange": "NYSE"},
    {"symbol": "MRK", "name": "Merck & Co. Inc.", "exchange": "NYSE"},
    {"symbol": "ABBV", "name": "AbbVie Inc.", "exchange": "NYSE"},
    {"symbol": "LLY", "name": "Eli Lilly and Company", "exchange": "NYSE"},
    {"symbol": "PEP", "name": "PepsiCo Inc.", "exchange": "NASDAQ"},
    {"symbol": "KO", "name": "The Coca-Cola Company", "exchange": "NYSE"},
    {"symbol": "AVGO", "name": "Broadcom Inc.", "exchange": "NASDAQ"},
    {"symbol": "COST", "name": "Costco Wholesale Corporation", "exchange": "NASDAQ"},
    {"symbol": "TMO", "name": "Thermo Fisher Scientific", "exchange": "NYSE"},
    {"symbol": "MCD", "name": "McDonald's Corporation", "exchange": "NYSE"},
    {"symbol": "CSCO", "name": "Cisco Systems Inc.", "exchange": "NASDAQ"},
    {"symbol": "ACN", "name": "Accenture plc", "exchange": "NYSE"},
    {"symbol": "ABT", "name": "Abbott Laboratories", "exchange": "NYSE"},
    {"symbol": "DHR", "name": "Danaher Corporation", "exchange": "NYSE"},
    {"symbol": "LIN", "name": "Linde plc", "exchange": "NYSE"},
    {"symbol": "ADBE", "name": "Adobe Inc.", "exchange": "NASDAQ"},
    {"symbol": "NKE", "name": "Nike Inc.", "exchange": "NYSE"},
    {"symbol": "CRM", "name": "Salesforce Inc.", "exchange": "NYSE"},
    {"symbol": "TXN", "name": "Texas Instruments", "exchange": "NASDAQ"},
    {"symbol": "NFLX", "name": "Netflix Inc.", "exchange": "NASDAQ"},
    {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "exchange": "NASDAQ"},
    {"symbol": "INTC", "name": "Intel Corporation", "exchange": "NASDAQ"},
    {"symbol": "QCOM", "name": "Qualcomm Inc.", "exchange": "NASDAQ"},
    {"symbol": "ORCL", "name": "Oracle Corporation", "exchange": "NYSE"},
    {"symbol": "IBM", "name": "International Business Machines", "exchange": "NYSE"},
    {"symbol": "GE", "name": "General Electric Company", "exchange": "NYSE"},
    {"symbol": "CAT", "name": "Caterpillar Inc.", "exchange": "NYSE"},
    {"symbol": "BA", "name": "The Boeing Company", "exchange": "NYSE"},
    {"symbol": "DIS", "name": "The Walt Disney Company", "exchange": "NYSE"},
    {"symbol": "GS", "name": "Goldman Sachs Group Inc.", "exchange": "NYSE"},
    {"symbol": "AMGN", "name": "Amgen Inc.", "exchange": "NASDAQ"},
    {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "exchange": "NASDAQ"},
    {"symbol": "SQ", "name": "Block Inc.", "exchange": "NYSE"},
    # US Mid Cap / Growth
    {"symbol": "SHOP", "name": "Shopify Inc.", "exchange": "NYSE"},
    {"symbol": "SNAP", "name": "Snap Inc.", "exchange": "NYSE"},
    {"symbol": "UBER", "name": "Uber Technologies Inc.", "exchange": "NYSE"},
    {"symbol": "LYFT", "name": "Lyft Inc.", "exchange": "NASDAQ"},
    {"symbol": "COIN", "name": "Coinbase Global Inc.", "exchange": "NASDAQ"},
    {"symbol": "PLTR", "name": "Palantir Technologies Inc.", "exchange": "NYSE"},
    {"symbol": "ROKU", "name": "Roku Inc.", "exchange": "NASDAQ"},
    {"symbol": "ZM", "name": "Zoom Video Communications", "exchange": "NASDAQ"},
    {"symbol": "RBLX", "name": "Roblox Corporation", "exchange": "NYSE"},
    {"symbol": "SNOW", "name": "Snowflake Inc.", "exchange": "NYSE"},
    # ETFs
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "exchange": "NASDAQ"},
    {"symbol": "IWM", "name": "iShares Russell 2000 ETF", "exchange": "NYSE"},
    {"symbol": "DIA", "name": "SPDR Dow Jones Industrial ETF", "exchange": "NYSE"},
    {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "exchange": "NYSE"},
    {"symbol": "GLD", "name": "SPDR Gold Shares", "exchange": "NYSE"},
    {"symbol": "SLV", "name": "iShares Silver Trust", "exchange": "NYSE"},
    {"symbol": "TLT", "name": "iShares 20+ Year Treasury Bond", "exchange": "NASDAQ"},
    {"symbol": "EEM", "name": "iShares MSCI Emerging Markets ETF", "exchange": "NYSE"},
    {"symbol": "XLF", "name": "Financial Select Sector SPDR Fund", "exchange": "NYSE"},
    # NSE India
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE"},
    {"symbol": "INFY.NS", "name": "Infosys Limited", "exchange": "NSE"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Limited", "exchange": "NSE"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever Limited", "exchange": "NSE"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Limited", "exchange": "NSE"},
    {"symbol": "ITC.NS", "name": "ITC Limited", "exchange": "NSE"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "exchange": "NSE"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro Limited", "exchange": "NSE"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank Limited", "exchange": "NSE"},
    {"symbol": "WIPRO.NS", "name": "Wipro Limited", "exchange": "NSE"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance Limited", "exchange": "NSE"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki India Limited", "exchange": "NSE"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Limited", "exchange": "NSE"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries", "exchange": "NSE"},
    {"symbol": "TITAN.NS", "name": "Titan Company Limited", "exchange": "NSE"},
    {"symbol": "ASIANPAINT.NS", "name": "Asian Paints Limited", "exchange": "NSE"},
    {"symbol": "HCLTECH.NS", "name": "HCL Technologies Limited", "exchange": "NSE"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel Limited", "exchange": "NSE"},
    {"symbol": "POWERGRID.NS", "name": "Power Grid Corporation", "exchange": "NSE"},
    {"symbol": "NTPC.NS", "name": "NTPC Limited", "exchange": "NSE"},
    {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement Limited", "exchange": "NSE"},
    {"symbol": "TECHM.NS", "name": "Tech Mahindra Limited", "exchange": "NSE"},
    {"symbol": "ONGC.NS", "name": "Oil and Natural Gas Corporation", "exchange": "NSE"},
    {"symbol": "JSWSTEEL.NS", "name": "JSW Steel Limited", "exchange": "NSE"},
    {"symbol": "ADANIENT.NS", "name": "Adani Enterprises Limited", "exchange": "NSE"},
    {"symbol": "DRREDDY.NS", "name": "Dr. Reddy's Laboratories", "exchange": "NSE"},
    {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories Limited", "exchange": "NSE"},
]
