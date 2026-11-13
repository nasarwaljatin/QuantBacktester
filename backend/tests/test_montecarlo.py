# backend/tests/test_montecarlo.py
"""Tests for the bootstrap Monte Carlo service.

Regression tests: the previous implementation shuffled the order of the same trades,
which keeps their sum, so all 1,000 paths ended at the same value and the
probability of profit could only be 0% or 100%.
"""

from app.services.montecarlo_service import run_monte_carlo

MIXED = [{"pnl": p} for p in (1200, -800, 450, -300, 2100, -1500, 600, -200)]
CAPITAL = 100_000.0


def test_final_values_vary_across_paths():
    result = run_monte_carlo(MIXED, n_simulations=1000, initial_capital=CAPITAL)
    assert len(result["final_values"]) == 1000
    assert len(set(round(v, 6) for v in result["final_values"])) > 1


def test_probability_of_profit_is_between_extremes_for_mixed_trades():
    result = run_monte_carlo(MIXED, initial_capital=CAPITAL)
    assert 0.0 < result["prob_profit"] < 100.0


def test_all_winning_trades_always_profit():
    result = run_monte_carlo([{"pnl": 100}, {"pnl": 250}], initial_capital=CAPITAL)
    assert result["prob_profit"] == 100.0
    assert result["max_drawdown_pct_p95"] == 0.0


def test_all_losing_trades_never_profit():
    result = run_monte_carlo([{"pnl": -100}, {"pnl": -250}], initial_capital=CAPITAL)
    assert result["prob_profit"] == 0.0
    assert result["max_drawdown_pct_p50"] > 0.0


def test_percentile_curves_are_ordered_and_spread():
    result = run_monte_carlo(MIXED, initial_capital=CAPITAL)
    p5, p50, p95 = result["percentile_5"], result["percentile_50"], result["percentile_95"]
    assert len(p5) == len(p50) == len(p95) == len(MIXED) + 1
    assert all(a <= b <= c for a, b, c in zip(p5, p50, p95))
    assert p5[-1] < p95[-1]


def test_drawdown_percentiles_are_ordered():
    result = run_monte_carlo(MIXED, initial_capital=CAPITAL)
    assert 0.0 <= result["max_drawdown_pct_p50"] <= result["max_drawdown_pct_p95"]


def test_same_seed_same_result():
    assert run_monte_carlo(MIXED, initial_capital=CAPITAL) == run_monte_carlo(MIXED, initial_capital=CAPITAL)


def test_sampled_paths_for_chart():
    result = run_monte_carlo(MIXED, n_simulations=1000, initial_capital=CAPITAL)
    assert len(result["paths"]) == 50
    assert all(len(p) == len(MIXED) + 1 and p[0] == CAPITAL for p in result["paths"])
    assert result["method"] == "bootstrap"


def test_no_trades_returns_flat_result():
    result = run_monte_carlo([], initial_capital=CAPITAL)
    assert result["paths"] == []
    assert result["final_values"] == [CAPITAL]
    assert result["prob_profit"] == 0.0
    assert result["max_drawdown_pct_p95"] == 0.0
