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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://finance.yahoo.com',
            'Origin': 'https://finance.yahoo.com',
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

    matches = []
    for entry in TICKER_LIST:
        symbol_lower = entry["symbol"].lower()
        name_lower = entry["name"].lower()

        score = 0
        if symbol_lower.startswith(query_lower):
            score += 10
        elif query_lower in symbol_lower:
            score += 5
        elif name_lower.startswith(query_lower):
            score += 8
        elif query_lower in name_lower:
            score += 3

        if score > 0:
            matches.append((score, entry))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches[:10]]



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
    # ── NSE India — Nifty 50 ─────────────────────────────────────────────────
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
    {"symbol": "POWERGRID.NS", "name": "Power Grid Corporation of India", "exchange": "NSE"},
    {"symbol": "NTPC.NS", "name": "NTPC Limited", "exchange": "NSE"},
    {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement Limited", "exchange": "NSE"},
    {"symbol": "TECHM.NS", "name": "Tech Mahindra Limited", "exchange": "NSE"},
    {"symbol": "ONGC.NS", "name": "Oil and Natural Gas Corporation", "exchange": "NSE"},
    {"symbol": "JSWSTEEL.NS", "name": "JSW Steel Limited", "exchange": "NSE"},
    {"symbol": "ADANIENT.NS", "name": "Adani Enterprises Limited", "exchange": "NSE"},
    {"symbol": "DRREDDY.NS", "name": "Dr. Reddy's Laboratories", "exchange": "NSE"},
    {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories Limited", "exchange": "NSE"},
    {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv Limited", "exchange": "NSE"},
    {"symbol": "NESTLEIND.NS", "name": "Nestle India Limited", "exchange": "NSE"},
    {"symbol": "CIPLA.NS", "name": "Cipla Limited", "exchange": "NSE"},
    {"symbol": "EICHERMOT.NS", "name": "Eicher Motors Limited", "exchange": "NSE"},
    {"symbol": "BPCL.NS", "name": "Bharat Petroleum Corporation", "exchange": "NSE"},
    {"symbol": "TATACONSUM.NS", "name": "Tata Consumer Products Limited", "exchange": "NSE"},
    {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals Enterprise", "exchange": "NSE"},
    {"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp Limited", "exchange": "NSE"},
    {"symbol": "INDUSINDBK.NS", "name": "IndusInd Bank Limited", "exchange": "NSE"},
    {"symbol": "GRASIM.NS", "name": "Grasim Industries Limited", "exchange": "NSE"},
    {"symbol": "COALINDIA.NS", "name": "Coal India Limited", "exchange": "NSE"},
    {"symbol": "BRITANNIA.NS", "name": "Britannia Industries Limited", "exchange": "NSE"},
    {"symbol": "SHRIRAMFIN.NS", "name": "Shriram Finance Limited", "exchange": "NSE"},
    {"symbol": "SBILIFE.NS", "name": "SBI Life Insurance Company", "exchange": "NSE"},
    {"symbol": "HDFCLIFE.NS", "name": "HDFC Life Insurance Company", "exchange": "NSE"},
    {"symbol": "M&M.NS", "name": "Mahindra & Mahindra Limited", "exchange": "NSE"},
    # ── NSE India — Adani Group ───────────────────────────────────────────────
    {"symbol": "ADANIPORTS.NS", "name": "Adani Ports and SEZ Limited", "exchange": "NSE"},
    {"symbol": "ADANIPOWER.NS", "name": "Adani Power Limited", "exchange": "NSE"},
    {"symbol": "ADANIGREEN.NS", "name": "Adani Green Energy Limited", "exchange": "NSE"},
    {"symbol": "ADANITRANS.NS", "name": "Adani Transmission Limited", "exchange": "NSE"},
    {"symbol": "ADANIGAS.NS", "name": "Adani Total Gas Limited", "exchange": "NSE"},
    {"symbol": "ADANIWILMAR.NS", "name": "Adani Wilmar Limited", "exchange": "NSE"},
    # ── NSE India — Nifty Next 50 & Large Mid-Caps ───────────────────────────
    {"symbol": "AMBUJACEM.NS", "name": "Ambuja Cements Limited", "exchange": "NSE"},
    {"symbol": "ACC.NS", "name": "ACC Limited", "exchange": "NSE"},
    {"symbol": "BAJAJ-AUTO.NS", "name": "Bajaj Auto Limited", "exchange": "NSE"},
    {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda", "exchange": "NSE"},
    {"symbol": "BERGEPAINT.NS", "name": "Berger Paints India Limited", "exchange": "NSE"},
    {"symbol": "BEL.NS", "name": "Bharat Electronics Limited", "exchange": "NSE"},
    {"symbol": "BHEL.NS", "name": "Bharat Heavy Electricals Limited", "exchange": "NSE"},
    {"symbol": "BIOCON.NS", "name": "Biocon Limited", "exchange": "NSE"},
    {"symbol": "BOSCHLTD.NS", "name": "Bosch Limited", "exchange": "NSE"},
    {"symbol": "CANBK.NS", "name": "Canara Bank", "exchange": "NSE"},
    {"symbol": "CHOLAFIN.NS", "name": "Cholamandalam Investment & Finance", "exchange": "NSE"},
    {"symbol": "COLPAL.NS", "name": "Colgate-Palmolive India Limited", "exchange": "NSE"},
    {"symbol": "DABUR.NS", "name": "Dabur India Limited", "exchange": "NSE"},
    {"symbol": "DLF.NS", "name": "DLF Limited", "exchange": "NSE"},
    {"symbol": "DMART.NS", "name": "Avenue Supermarts Limited (DMart)", "exchange": "NSE"},
    {"symbol": "FEDERALBNK.NS", "name": "Federal Bank Limited", "exchange": "NSE"},
    {"symbol": "GAIL.NS", "name": "GAIL India Limited", "exchange": "NSE"},
    {"symbol": "GODREJCP.NS", "name": "Godrej Consumer Products Limited", "exchange": "NSE"},
    {"symbol": "GODREJPROP.NS", "name": "Godrej Properties Limited", "exchange": "NSE"},
    {"symbol": "HAVELLS.NS", "name": "Havells India Limited", "exchange": "NSE"},
    {"symbol": "HAL.NS", "name": "Hindustan Aeronautics Limited", "exchange": "NSE"},
    {"symbol": "HINDCOPPER.NS", "name": "Hindustan Copper Limited", "exchange": "NSE"},
    {"symbol": "HINDALCO.NS", "name": "Hindalco Industries Limited", "exchange": "NSE"},
    {"symbol": "ICICIGI.NS", "name": "ICICI Lombard General Insurance", "exchange": "NSE"},
    {"symbol": "IDFCFIRSTB.NS", "name": "IDFC First Bank Limited", "exchange": "NSE"},
    {"symbol": "INDUSTOWER.NS", "name": "Indus Towers Limited", "exchange": "NSE"},
    {"symbol": "IOC.NS", "name": "Indian Oil Corporation Limited", "exchange": "NSE"},
    {"symbol": "IRCTC.NS", "name": "Indian Railway Catering & Tourism", "exchange": "NSE"},
    {"symbol": "IRFC.NS", "name": "Indian Railway Finance Corporation", "exchange": "NSE"},
    {"symbol": "JINDALSTEL.NS", "name": "Jindal Steel & Power Limited", "exchange": "NSE"},
    {"symbol": "JUBLFOOD.NS", "name": "Jubilant Foodworks Limited", "exchange": "NSE"},
    {"symbol": "LTIM.NS", "name": "LTIMindtree Limited", "exchange": "NSE"},
    {"symbol": "LTTS.NS", "name": "L&T Technology Services", "exchange": "NSE"},
    {"symbol": "LUPIN.NS", "name": "Lupin Limited", "exchange": "NSE"},
    {"symbol": "MARICO.NS", "name": "Marico Limited", "exchange": "NSE"},
    {"symbol": "MFSL.NS", "name": "Max Financial Services Limited", "exchange": "NSE"},
    {"symbol": "MOTHERSON.NS", "name": "Samvardhana Motherson International", "exchange": "NSE"},
    {"symbol": "MPHASIS.NS", "name": "Mphasis Limited", "exchange": "NSE"},
    {"symbol": "MRF.NS", "name": "MRF Limited", "exchange": "NSE"},
    {"symbol": "NAUKRI.NS", "name": "Info Edge India Limited (Naukri)", "exchange": "NSE"},
    {"symbol": "NMDC.NS", "name": "NMDC Limited", "exchange": "NSE"},
    {"symbol": "OBEROIRLTY.NS", "name": "Oberoi Realty Limited", "exchange": "NSE"},
    {"symbol": "OFSS.NS", "name": "Oracle Financial Services Software", "exchange": "NSE"},
    {"symbol": "PAGEIND.NS", "name": "Page Industries Limited", "exchange": "NSE"},
    {"symbol": "PERSISTENT.NS", "name": "Persistent Systems Limited", "exchange": "NSE"},
    {"symbol": "PETRONET.NS", "name": "Petronet LNG Limited", "exchange": "NSE"},
    {"symbol": "PIDILITIND.NS", "name": "Pidilite Industries Limited", "exchange": "NSE"},
    {"symbol": "PIIND.NS", "name": "PI Industries Limited", "exchange": "NSE"},
    {"symbol": "PNB.NS", "name": "Punjab National Bank", "exchange": "NSE"},
    {"symbol": "POLYCAB.NS", "name": "Polycab India Limited", "exchange": "NSE"},
    {"symbol": "PFC.NS", "name": "Power Finance Corporation", "exchange": "NSE"},
    {"symbol": "RECLTD.NS", "name": "REC Limited", "exchange": "NSE"},
    {"symbol": "SAIL.NS", "name": "Steel Authority of India", "exchange": "NSE"},
    {"symbol": "SIEMENS.NS", "name": "Siemens Limited", "exchange": "NSE"},
    {"symbol": "SRF.NS", "name": "SRF Limited", "exchange": "NSE"},
    {"symbol": "SUZLON.NS", "name": "Suzlon Energy Limited", "exchange": "NSE"},
    {"symbol": "TATAPOWER.NS", "name": "Tata Power Company Limited", "exchange": "NSE"},
    {"symbol": "TATACOMM.NS", "name": "Tata Communications Limited", "exchange": "NSE"},
    {"symbol": "TATAELXSI.NS", "name": "Tata Elxsi Limited", "exchange": "NSE"},
    {"symbol": "TATACHEM.NS", "name": "Tata Chemicals Limited", "exchange": "NSE"},
    {"symbol": "TORNTPHARM.NS", "name": "Torrent Pharmaceuticals Limited", "exchange": "NSE"},
    {"symbol": "TORNTPOWER.NS", "name": "Torrent Power Limited", "exchange": "NSE"},
    {"symbol": "TRENT.NS", "name": "Trent Limited", "exchange": "NSE"},
    {"symbol": "TRIDENT.NS", "name": "Trident Limited", "exchange": "NSE"},
    {"symbol": "UBL.NS", "name": "United Breweries Limited", "exchange": "NSE"},
    {"symbol": "UNIONBANK.NS", "name": "Union Bank of India", "exchange": "NSE"},
    {"symbol": "UPL.NS", "name": "UPL Limited", "exchange": "NSE"},
    {"symbol": "VEDL.NS", "name": "Vedanta Limited", "exchange": "NSE"},
    {"symbol": "VOLTAS.NS", "name": "Voltas Limited", "exchange": "NSE"},
    {"symbol": "ZOMATO.NS", "name": "Zomato Limited", "exchange": "NSE"},
    {"symbol": "NYKAA.NS", "name": "FSN E-Commerce Ventures (Nykaa)", "exchange": "NSE"},
    {"symbol": "PAYTM.NS", "name": "One97 Communications Limited (Paytm)", "exchange": "NSE"},
    # ── NSE India — Banking & Finance ─────────────────────────────────────────
    {"symbol": "AUBANK.NS", "name": "AU Small Finance Bank", "exchange": "NSE"},
    {"symbol": "BANDHANBNK.NS", "name": "Bandhan Bank Limited", "exchange": "NSE"},
    {"symbol": "EQUITASBNK.NS", "name": "Equitas Small Finance Bank", "exchange": "NSE"},
    {"symbol": "HDFCAMC.NS", "name": "HDFC Asset Management Company", "exchange": "NSE"},
    {"symbol": "ICICIPRU.NS", "name": "ICICI Prudential Life Insurance", "exchange": "NSE"},
    {"symbol": "ISEC.NS", "name": "ICICI Securities Limited", "exchange": "NSE"},
    {"symbol": "JIOFIN.NS", "name": "Jio Financial Services Limited", "exchange": "NSE"},
    {"symbol": "KARURVYSYA.NS", "name": "Karur Vysya Bank", "exchange": "NSE"},
    {"symbol": "MANAPPURAM.NS", "name": "Manappuram Finance Limited", "exchange": "NSE"},
    {"symbol": "MUTHOOTFIN.NS", "name": "Muthoot Finance Limited", "exchange": "NSE"},
    {"symbol": "RBLBANK.NS", "name": "RBL Bank Limited", "exchange": "NSE"},
    {"symbol": "SBICARD.NS", "name": "SBI Cards and Payment Services", "exchange": "NSE"},
    {"symbol": "STARHEALTH.NS", "name": "Star Health and Allied Insurance", "exchange": "NSE"},
    {"symbol": "SUNDARMFIN.NS", "name": "Sundaram Finance Limited", "exchange": "NSE"},
    {"symbol": "IIFL.NS", "name": "IIFL Finance Limited", "exchange": "NSE"},
    {"symbol": "INDIANB.NS", "name": "Indian Bank", "exchange": "NSE"},
    # ── NSE India — IT & Technology ───────────────────────────────────────────
    {"symbol": "COFORGE.NS", "name": "Coforge Limited", "exchange": "NSE"},
    {"symbol": "CYIENT.NS", "name": "Cyient Limited", "exchange": "NSE"},
    {"symbol": "KPIT.NS", "name": "KPIT Technologies Limited", "exchange": "NSE"},
    {"symbol": "TANLA.NS", "name": "Tanla Platforms Limited", "exchange": "NSE"},
    {"symbol": "TATATECH.NS", "name": "Tata Technologies Limited", "exchange": "NSE"},
    {"symbol": "ZENSARTECH.NS", "name": "Zensar Technologies Limited", "exchange": "NSE"},
    {"symbol": "ROUTE.NS", "name": "Route Mobile Limited", "exchange": "NSE"},
    {"symbol": "INTELLECT.NS", "name": "Intellect Design Arena Limited", "exchange": "NSE"},
    # ── NSE India — Pharma & Healthcare ──────────────────────────────────────
    {"symbol": "AUROPHARMA.NS", "name": "Aurobindo Pharma Limited", "exchange": "NSE"},
    {"symbol": "ALKEM.NS", "name": "Alkem Laboratories Limited", "exchange": "NSE"},
    {"symbol": "GLAND.NS", "name": "Gland Pharma Limited", "exchange": "NSE"},
    {"symbol": "GRANULES.NS", "name": "Granules India Limited", "exchange": "NSE"},
    {"symbol": "IPCA.NS", "name": "Ipca Laboratories Limited", "exchange": "NSE"},
    {"symbol": "JBCHEPHARM.NS", "name": "JB Chemicals & Pharmaceuticals", "exchange": "NSE"},
    {"symbol": "LALPATHLAB.NS", "name": "Dr. Lal PathLabs Limited", "exchange": "NSE"},
    {"symbol": "LAURUSLABS.NS", "name": "Laurus Labs Limited", "exchange": "NSE"},
    {"symbol": "MAXHEALTH.NS", "name": "Max Healthcare Institute Limited", "exchange": "NSE"},
    {"symbol": "METROPOLIS.NS", "name": "Metropolis Healthcare Limited", "exchange": "NSE"},
    {"symbol": "NATCOPHARM.NS", "name": "Natco Pharma Limited", "exchange": "NSE"},
    {"symbol": "SYNGENE.NS", "name": "Syngene International Limited", "exchange": "NSE"},
    {"symbol": "FORTIS.NS", "name": "Fortis Healthcare Limited", "exchange": "NSE"},
    {"symbol": "NH.NS", "name": "Narayana Hrudayalaya Limited", "exchange": "NSE"},
    {"symbol": "ZYDUSLIFE.NS", "name": "Zydus Lifesciences Limited", "exchange": "NSE"},
    # ── NSE India — Auto & Auto Ancillaries ──────────────────────────────────
    {"symbol": "ASHOKLEY.NS", "name": "Ashok Leyland Limited", "exchange": "NSE"},
    {"symbol": "BALKRISIND.NS", "name": "Balkrishna Industries Limited", "exchange": "NSE"},
    {"symbol": "BHARATFORG.NS", "name": "Bharat Forge Limited", "exchange": "NSE"},
    {"symbol": "CEAT.NS", "name": "CEAT Limited", "exchange": "NSE"},
    {"symbol": "ESCORTS.NS", "name": "Escorts Kubota Limited", "exchange": "NSE"},
    {"symbol": "EXIDEIND.NS", "name": "Exide Industries Limited", "exchange": "NSE"},
    {"symbol": "JKTYRE.NS", "name": "JK Tyre & Industries Limited", "exchange": "NSE"},
    {"symbol": "TIINDIA.NS", "name": "Tube Investments of India", "exchange": "NSE"},
    {"symbol": "TVSMOTOR.NS", "name": "TVS Motor Company Limited", "exchange": "NSE"},
    {"symbol": "APOLLOTYRE.NS", "name": "Apollo Tyres Limited", "exchange": "NSE"},
    # ── NSE India — FMCG & Consumer ───────────────────────────────────────────
    {"symbol": "EMAMILTD.NS", "name": "Emami Limited", "exchange": "NSE"},
    {"symbol": "JYOTHYLAB.NS", "name": "Jyothy Labs Limited", "exchange": "NSE"},
    {"symbol": "RADICO.NS", "name": "Radico Khaitan Limited", "exchange": "NSE"},
    {"symbol": "VBL.NS", "name": "Varun Beverages Limited", "exchange": "NSE"},
    # ── NSE India — Energy & Oil ───────────────────────────────────────────────
    {"symbol": "CASTROLIND.NS", "name": "Castrol India Limited", "exchange": "NSE"},
    {"symbol": "GUJGASLTD.NS", "name": "Gujarat Gas Limited", "exchange": "NSE"},
    {"symbol": "HINDPETRO.NS", "name": "Hindustan Petroleum Corporation", "exchange": "NSE"},
    {"symbol": "IGL.NS", "name": "Indraprastha Gas Limited", "exchange": "NSE"},
    {"symbol": "MGL.NS", "name": "Mahanagar Gas Limited", "exchange": "NSE"},
    {"symbol": "OIL.NS", "name": "Oil India Limited", "exchange": "NSE"},
    # ── NSE India — Infrastructure & Real Estate ─────────────────────────────
    {"symbol": "BRIGADE.NS", "name": "Brigade Enterprises Limited", "exchange": "NSE"},
    {"symbol": "GMRINFRA.NS", "name": "GMR Airports Infrastructure", "exchange": "NSE"},
    {"symbol": "IRB.NS", "name": "IRB Infrastructure Developers", "exchange": "NSE"},
    {"symbol": "LODHA.NS", "name": "Macrotech Developers Limited (Lodha)", "exchange": "NSE"},
    {"symbol": "PRESTIGE.NS", "name": "Prestige Estates Projects", "exchange": "NSE"},
    {"symbol": "SOBHA.NS", "name": "Sobha Limited", "exchange": "NSE"},
    {"symbol": "PHOENIXLTD.NS", "name": "The Phoenix Mills Limited", "exchange": "NSE"},
    # ── NSE India — Telecom ───────────────────────────────────────────────────
    {"symbol": "IDEA.NS", "name": "Vodafone Idea Limited", "exchange": "NSE"},
    {"symbol": "MTNL.NS", "name": "Mahanagar Telephone Nigam", "exchange": "NSE"},
    # ── NSE India — Metals & Mining ───────────────────────────────────────────
    {"symbol": "APLAPOLLO.NS", "name": "APL Apollo Tubes Limited", "exchange": "NSE"},
    {"symbol": "HINDZINC.NS", "name": "Hindustan Zinc Limited", "exchange": "NSE"},
    {"symbol": "NATIONALUM.NS", "name": "National Aluminium Company", "exchange": "NSE"},
    {"symbol": "RATNAMANI.NS", "name": "Ratnamani Metals & Tubes Limited", "exchange": "NSE"},
    {"symbol": "WELCORP.NS", "name": "Welspun Corp Limited", "exchange": "NSE"},
    # ── NSE India — Chemicals & Fertilizers ──────────────────────────────────
    {"symbol": "AARTIIND.NS", "name": "Aarti Industries Limited", "exchange": "NSE"},
    {"symbol": "CHAMBLFERT.NS", "name": "Chambal Fertilisers & Chemicals", "exchange": "NSE"},
    {"symbol": "COROMANDEL.NS", "name": "Coromandel International Limited", "exchange": "NSE"},
    {"symbol": "DEEPAKNTR.NS", "name": "Deepak Nitrite Limited", "exchange": "NSE"},
    {"symbol": "GNFC.NS", "name": "Gujarat Narmada Valley Fertilizers", "exchange": "NSE"},
    {"symbol": "GSFC.NS", "name": "Gujarat State Fertilizers & Chemicals", "exchange": "NSE"},
    # ── NSE India — Capital Goods & Defence ──────────────────────────────────
    {"symbol": "ABB.NS", "name": "ABB India Limited", "exchange": "NSE"},
    {"symbol": "AIAENG.NS", "name": "AIA Engineering Limited", "exchange": "NSE"},
    {"symbol": "BDL.NS", "name": "Bharat Dynamics Limited", "exchange": "NSE"},
    {"symbol": "CGPOWER.NS", "name": "CG Power and Industrial Solutions", "exchange": "NSE"},
    {"symbol": "COCHINSHIP.NS", "name": "Cochin Shipyard Limited", "exchange": "NSE"},
    {"symbol": "CUMMINSIND.NS", "name": "Cummins India Limited", "exchange": "NSE"},
    {"symbol": "HFCL.NS", "name": "HFCL Limited", "exchange": "NSE"},
    {"symbol": "KEC.NS", "name": "KEC International Limited", "exchange": "NSE"},
    {"symbol": "MAZAGONDOCK.NS", "name": "Mazagon Dock Shipbuilders", "exchange": "NSE"},
    {"symbol": "RVNL.NS", "name": "Rail Vikas Nigam Limited", "exchange": "NSE"},
    {"symbol": "THERMAX.NS", "name": "Thermax Limited", "exchange": "NSE"},
    {"symbol": "TITAGARH.NS", "name": "Titagarh Rail Systems Limited", "exchange": "NSE"},
    {"symbol": "TRITURBINE.NS", "name": "Triveni Turbine Limited", "exchange": "NSE"},
    {"symbol": "HONAUT.NS", "name": "Honeywell Automation India", "exchange": "NSE"},
    # ── NSE India — Retail & Fashion ─────────────────────────────────────────
    {"symbol": "ABFRL.NS", "name": "Aditya Birla Fashion & Retail", "exchange": "NSE"},
    {"symbol": "BATAINDIA.NS", "name": "Bata India Limited", "exchange": "NSE"},
    {"symbol": "RAYMOND.NS", "name": "Raymond Limited", "exchange": "NSE"},
    {"symbol": "SHOPERSTOP.NS", "name": "Shoppers Stop Limited", "exchange": "NSE"},
    {"symbol": "VMART.NS", "name": "V-Mart Retail Limited", "exchange": "NSE"},
    {"symbol": "KPRMILL.NS", "name": "K.P.R. Mill Limited", "exchange": "NSE"},
    # ── NSE India — Media & Entertainment ────────────────────────────────────
    {"symbol": "NAZARA.NS", "name": "Nazara Technologies Limited", "exchange": "NSE"},
    {"symbol": "PVRINOX.NS", "name": "PVR INOX Limited", "exchange": "NSE"},
    {"symbol": "SUNTV.NS", "name": "Sun TV Network Limited", "exchange": "NSE"},
    {"symbol": "ZEEL.NS", "name": "Zee Entertainment Enterprises", "exchange": "NSE"},
    # ── NSE India — Cement ────────────────────────────────────────────────────
    {"symbol": "HEIDELBERG.NS", "name": "HeidelbergCement India", "exchange": "NSE"},
    {"symbol": "INDIACEM.NS", "name": "The India Cements Limited", "exchange": "NSE"},
    {"symbol": "JKCEMENT.NS", "name": "JK Cement Limited", "exchange": "NSE"},
    {"symbol": "RAMCOCEM.NS", "name": "The Ramco Cements Limited", "exchange": "NSE"},
    {"symbol": "SHREECEM.NS", "name": "Shree Cement Limited", "exchange": "NSE"},
    # ── NSE India — PSU / Government ─────────────────────────────────────────
    {"symbol": "CDSL.NS", "name": "Central Depository Services India", "exchange": "NSE"},
    {"symbol": "CONCOR.NS", "name": "Container Corporation of India", "exchange": "NSE"},
    {"symbol": "GICRE.NS", "name": "General Insurance Corporation", "exchange": "NSE"},
    {"symbol": "HUDCO.NS", "name": "Housing & Urban Development Corp", "exchange": "NSE"},
    {"symbol": "MCX.NS", "name": "Multi Commodity Exchange of India", "exchange": "NSE"},
    {"symbol": "NBCC.NS", "name": "NBCC India Limited", "exchange": "NSE"},
    {"symbol": "NHPC.NS", "name": "NHPC Limited", "exchange": "NSE"},
    {"symbol": "RITES.NS", "name": "RITES Limited", "exchange": "NSE"},
    {"symbol": "SJVN.NS", "name": "SJVN Limited", "exchange": "NSE"},
    # ── NSE India — New-Age / Startup Listings ────────────────────────────────
    {"symbol": "DELHIVERY.NS", "name": "Delhivery Limited", "exchange": "NSE"},
    {"symbol": "EASEMYTRIP.NS", "name": "Easy Trip Planners Limited", "exchange": "NSE"},
    {"symbol": "IXIGO.NS", "name": "Le Travenues Technology (Ixigo)", "exchange": "NSE"},
    {"symbol": "MAMAEARTH.NS", "name": "Honasa Consumer Limited (Mamaearth)", "exchange": "NSE"},
    {"symbol": "POLICYBZR.NS", "name": "PB Fintech Limited (PolicyBazaar)", "exchange": "NSE"},
    {"symbol": "SWIGGY.NS", "name": "Bundl Technologies Limited (Swiggy)", "exchange": "NSE"},
]
