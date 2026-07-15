# QuantBacktester

[![MIT License](https://img.shields.io/badge/License-MIT-cyan.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

> A web-based algorithmic trading strategy backtesting platform. Write strategies in Python, test against real historical data, and analyze performance with interactive charts.

![QuantBacktester Screenshot](screenshot_placeholder.png)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/youruser/quantbacktester.git
cd quantbacktester

# 2. Copy environment variables
cp .env.example .env

# 3. Launch all services
docker compose up --build

# 4. Open in browser
open http://localhost:3000
```

The platform will be available at `http://localhost:3000` with the API at `http://localhost:8000`.

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────┐
│   Browser   │────▶│  Next.js 14      │     │          │
│  (User)     │◀────│  Frontend :3000  │     │  Redis   │
└─────────────┘     └──────────────────┘     │  :6379   │
                             │               └────┬─────┘
                             │                    │
                             ▼                    │
                    ┌──────────────────┐          │
                    │  FastAPI         │◀─────────┘
                    │  Backend :8000   │
                    └────┬────────┬────┘
                         │        │
                         ▼        ▼
                 ┌───────────┐  ┌──────────┐
                 │PostgreSQL │  │  Celery   │
                 │  :5432    │  │  Worker   │
                 └───────────┘  └──────────┘
```

### Data Flow
1. User writes strategy in Monaco Editor → submits via REST API
2. FastAPI validates input → dispatches Celery task
3. Celery worker fetches OHLCV data (yfinance, cached in PostgreSQL)
4. Backtrader runs the strategy → extracts equity curve + trades
5. Metrics service computes Sharpe, Sortino, drawdown, etc.
6. Monte Carlo service runs 1000 simulations
7. Results stored in PostgreSQL → returned to frontend
8. Frontend renders interactive Plotly charts + metrics grid

---

## Supported Metrics

| Metric | Description |
|--------|-------------|
| **Total Return** | Cumulative portfolio gain/loss over the backtest period |
| **Annualized Return** | Compound annual growth rate (CAGR) |
| **Sharpe Ratio** | Risk-adjusted return (excess return / volatility) |
| **Sortino Ratio** | Like Sharpe, but only penalizes downside volatility |
| **Max Drawdown** | Largest peak-to-trough decline during the backtest |
| **Calmar Ratio** | Annualized return / |max drawdown| |
| **Win Rate** | Percentage of profitable trades |
| **Profit Factor** | Gross profit / gross loss |
| **Total Trades** | Number of completed round-trip trades |
| **Avg Holding Period** | Average trade duration in calendar days |

---

## Strategy DSL Reference

Strategies are written as Python classes extending `bt.Strategy` from the Backtrader library. The following are pre-imported in the sandbox:

- `bt` — Backtrader library
- `np` — NumPy
- `pd` — Pandas

### Example Strategy

```python
class UserStrategy(bt.Strategy):
    params = dict(fast=50, slow=200)

    def __init__(self):
        self.fast_ma = bt.ind.SMA(period=self.p.fast)
        self.slow_ma = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
```

### Key Methods
- `__init__()` — Define indicators
- `next()` — Called on each bar; implement trading logic
- `self.buy()` / `self.sell()` / `self.close()` — Execute orders
- `self.position` — Current position info
- `self.data.close[0]` — Current close price

---

## Built-in Strategy Templates

| Strategy | Description |
|----------|-------------|
| **SMA Crossover** | Buy when 50-day SMA crosses above 200-day SMA |
| **EMA Crossover (3/30)** | Buy when 3-period EMA crosses above 30-period EMA |
| **RSI Mean Reversion** | Buy when RSI(14) < 30, sell when > 70 |
| **Bollinger Bands** | Buy below lower band, sell above upper band |
| **MACD** | Buy on MACD/signal line bullish crossover |

---

## Tech Stack

### Backend
- FastAPI, Backtrader, yfinance, pandas, numpy, scipy
- Celery + Redis for async task processing
- PostgreSQL + SQLAlchemy for data persistence
- Pydantic v2 for validation

### Frontend
- Next.js 14 (App Router), TypeScript
- Monaco Editor (in-browser code editor)
- Plotly.js (interactive charts)
- TailwindCSS (styling)
- Zustand (state management)
- TanStack Query (data fetching)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
