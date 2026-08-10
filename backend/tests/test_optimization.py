# backend/tests/test_optimization.py
"""Unit tests for parameter sweep and walk-forward analysis utilities."""

import pytest
from datetime import date

from app.engine.optimizer import (
    generate_param_combinations,
    split_walk_forward_windows,
    select_best_params,
)


# ─── generate_param_combinations ────────────────────────────────────────────

class TestGenerateParamCombinations:
    def test_single_param(self):
        grid = {"fast": [3, 5, 10]}
        combos = generate_param_combinations(grid)
        assert len(combos) == 3
        assert {"fast": 3} in combos
        assert {"fast": 10} in combos

    def test_two_params(self):
        grid = {"fast": [3, 5], "slow": [20, 30]}
        combos = generate_param_combinations(grid)
        assert len(combos) == 4
        assert {"fast": 3, "slow": 20} in combos
        assert {"fast": 5, "slow": 30} in combos

    def test_three_params(self):
        grid = {"a": [1, 2], "b": [10, 20], "c": [100]}
        combos = generate_param_combinations(grid)
        assert len(combos) == 4  # 2 * 2 * 1

    def test_single_value_per_param(self):
        grid = {"fast": [5], "slow": [20]}
        combos = generate_param_combinations(grid)
        assert combos == [{"fast": 5, "slow": 20}]

    def test_empty_grid_raises(self):
        with pytest.raises(ValueError, match="empty"):
            generate_param_combinations({})

    def test_empty_value_list_raises(self):
        with pytest.raises(ValueError, match="'fast'"):
            generate_param_combinations({"fast": [], "slow": [20]})

    def test_string_values_supported(self):
        grid = {"mode": ["aggressive", "conservative"]}
        combos = generate_param_combinations(grid)
        assert len(combos) == 2
        assert {"mode": "aggressive"} in combos


# ─── split_walk_forward_windows ─────────────────────────────────────────────

class TestSplitWalkForwardWindows:
    def test_basic_two_windows(self):
        # 2 * (365 + 90) = 910 days needed for 2 complete windows
        start = date(2018, 1, 1)
        end = date(2021, 1, 1)  # ~1096 days
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90)
        assert len(windows) >= 2

    def test_window_structure(self):
        start = date(2020, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=180, out_of_sample_days=90)
        for w in windows:
            assert "in_sample_start" in w
            assert "in_sample_end" in w
            assert "out_of_sample_start" in w
            assert "out_of_sample_end" in w

    def test_no_oos_overlap(self):
        """Out-of-sample periods must not overlap."""
        start = date(2018, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90)
        for i in range(len(windows) - 1):
            # Current OOS ends before next OOS starts
            assert windows[i]["out_of_sample_end"] < windows[i + 1]["out_of_sample_start"]

    def test_is_immediately_precedes_oos(self):
        """In-sample end must be exactly one day before OOS start."""
        from datetime import timedelta
        start = date(2018, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90)
        for w in windows:
            assert w["in_sample_end"] + timedelta(days=1) == w["out_of_sample_start"]

    def test_too_short_raises(self):
        start = date(2020, 1, 1)
        end = date(2020, 6, 1)  # only ~152 days, need 365+90=455
        with pytest.raises(ValueError, match="too short"):
            split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90)

    def test_invalid_in_sample_raises(self):
        with pytest.raises(ValueError):
            split_walk_forward_windows(date(2020, 1, 1), date(2022, 1, 1), in_sample_days=0, out_of_sample_days=90)

    def test_invalid_oos_raises(self):
        with pytest.raises(ValueError):
            split_walk_forward_windows(date(2020, 1, 1), date(2022, 1, 1), in_sample_days=365, out_of_sample_days=0)


# ─── select_best_params ──────────────────────────────────────────────────────

class TestSelectBestParams:
    def test_selects_highest_objective(self):
        results = [
            {"parameters": {"fast": 3, "slow": 20}, "metrics": {"sharpe_ratio": 0.5}, "status": "SUCCESS"},
            {"parameters": {"fast": 5, "slow": 30}, "metrics": {"sharpe_ratio": 1.2}, "status": "SUCCESS"},
            {"parameters": {"fast": 10, "slow": 50}, "metrics": {"sharpe_ratio": 0.8}, "status": "SUCCESS"},
        ]
        best = select_best_params(results, objective="sharpe_ratio")
        assert best == {"fast": 5, "slow": 30}

    def test_ignores_failed_results(self):
        results = [
            {"parameters": {"fast": 3}, "metrics": {"sharpe_ratio": 5.0}, "status": "FAILURE"},
            {"parameters": {"fast": 5}, "metrics": {"sharpe_ratio": 1.2}, "status": "SUCCESS"},
        ]
        best = select_best_params(results, objective="sharpe_ratio")
        assert best == {"fast": 5}

    def test_empty_results_raises(self):
        with pytest.raises(ValueError, match="empty"):
            select_best_params([], objective="sharpe_ratio")

    def test_all_failed_raises(self):
        results = [
            {"parameters": {"fast": 3}, "metrics": None, "status": "FAILURE"},
        ]
        with pytest.raises(ValueError, match="No successful"):
            select_best_params(results, objective="sharpe_ratio")

    def test_custom_objective(self):
        results = [
            {"parameters": {"fast": 3}, "metrics": {"total_return": 0.1, "sharpe_ratio": 1.5}, "status": "SUCCESS"},
            {"parameters": {"fast": 5}, "metrics": {"total_return": 0.5, "sharpe_ratio": 0.8}, "status": "SUCCESS"},
        ]
        best = select_best_params(results, objective="total_return")
        assert best == {"fast": 5}

    def test_handles_none_metric(self):
        results = [
            {"parameters": {"fast": 3}, "metrics": {"sharpe_ratio": None}, "status": "SUCCESS"},
            {"parameters": {"fast": 5}, "metrics": {"sharpe_ratio": 1.2}, "status": "SUCCESS"},
        ]
        best = select_best_params(results, objective="sharpe_ratio")
        assert best == {"fast": 5}
