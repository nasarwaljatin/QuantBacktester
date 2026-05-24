# backend/tests/test_api.py
"""Integration tests for the FastAPI backend API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine


@pytest.fixture(scope="module", autouse=True)
def init_db():
    """Ensure database tables are initialized for testing."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_health_check(client):
    """Verify that the health check endpoint returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "QuantBacktester"}


def test_ticker_search(client):
    """Verify that search_tickers endpoint works for common symbols."""
    response = client.get("/api/tickers/search?q=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert isinstance(results, list)
    assert len(results) > 0
    assert any(item["symbol"] == "AAPL" for item in results)


def test_submit_backtest_invalid_dates(client):
    """Verify backtest endpoint returns 400 Bad Request if start_date >= end_date."""
    payload = {
        "strategy_code": "class UserStrategy(bt.Strategy): pass",
        "ticker": "AAPL",
        "start_date": "2023-12-31",
        "end_date": "2023-01-01",  # Invalid
        "config": {
            "initial_capital": 100000.0,
            "commission": 0.001,
            "slippage": 0.0005
        }
    }
    response = client.post("/api/backtest", json=payload)
    assert response.status_code == 400
    assert "error" in response.json()["detail"]


def test_submit_and_poll_backtest_local(client):
    """Verify the end-to-end submit and polling flow for local execution."""
    payload = {
        "strategy_code": "class UserStrategy(bt.Strategy):\n    def next(self):\n        pass",
        "ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-01-10",
        "config": {
            "initial_capital": 100000.0,
            "commission": 0.001,
            "slippage": 0.0005
        }
    }
    
    # Submit the backtest
    response = client.post("/api/backtest", json=payload)
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    assert task_id is not None
    
    # Poll for results
    response = client.get(f"/api/backtest/{task_id}")
    assert response.status_code == 200
    status = response.json()["status"]
    
    # Since we are running in the TestClient, FastAPI's BackgroundTasks are executed
    # synchronously during the request-response lifecycle (on shutdown of request context).
    # Thus, when the request returns, the task has already executed and completed!
    assert status == "success"
    assert "metrics" in response.json()
    assert "equity_curve" in response.json()
