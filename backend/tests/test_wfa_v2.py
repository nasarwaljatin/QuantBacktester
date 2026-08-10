"""WFA v2 addon tests — appended to test_optimization.py via concatenation."""

# This file is imported/included by concatenation; run it with:
#   python -m pytest backend/tests/test_optimization.py
# The imports and class definitions below extend the test suite.

import pytest
from datetime import date

from app.engine.optimizer import (
    split_walk_forward_windows,
    generate_param_combinations,
    compute_efficiency_ratio,
    compute_param_stability,
    validate_wfa_config,
)
from app.services.walk_forward_service import estimate_wfa_runs


class TestExpandingWindows:
    def test_expanding_is_start_pinned(self):
        start = date(2018, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90, window_type="expanding")
        for w in windows:
            assert w["in_sample_start"] == start

    def test_expanding_is_grows(self):
        start = date(2018, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90, window_type="expanding")
        for i in range(1, len(windows)):
            assert windows[i]["in_sample_end"] > windows[i - 1]["in_sample_end"]

    def test_expanding_oos_consecutive(self):
        start = date(2018, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90, window_type="expanding")
        for i in range(len(windows) - 1):
            assert windows[i]["out_of_sample_end"] < windows[i + 1]["out_of_sample_start"]


class TestAnchoredRolling:
    def test_anchored_is_start_pinned(self):
        start = date(2018, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90, window_type="rolling", anchored=True)
        first = windows[0]["in_sample_start"]
        for w in windows:
            assert w["in_sample_start"] == first

    def test_anchored_oos_slides(self):
        start = date(2018, 1, 1)
        end = date(2022, 1, 1)
        windows = split_walk_forward_windows(start, end, in_sample_days=365, out_of_sample_days=90, window_type="rolling", anchored=True)
        for i in range(1, len(windows)):
            assert windows[i]["out_of_sample_start"] > windows[i - 1]["out_of_sample_start"]


class TestComputeEfficiencyRatio:
    def test_positive_equal(self):
        assert compute_efficiency_ratio(1.0, 1.0) == pytest.approx(1.0)

    def test_ratio_half(self):
        assert compute_efficiency_ratio(2.0, 1.0) == pytest.approx(0.5)

    def test_none_is_returns_none(self):
        assert compute_efficiency_ratio(None, 1.0) is None

    def test_none_oos_returns_none(self):
        assert compute_efficiency_ratio(1.0, None) is None

    def test_zero_is_returns_none(self):
        assert compute_efficiency_ratio(0.0, 0.5) is None


class TestComputeParamStability:
    def test_stable_params_cv_zero(self):
        params_list = [{"fast": 5, "slow": 20}] * 4
        stability = compute_param_stability(params_list)
        assert stability.get("fast") == pytest.approx(0.0, abs=1e-9)

    def test_varying_params_positive_cv(self):
        params_list = [{"fast": 5}, {"fast": 10}, {"fast": 15}, {"fast": 20}]
        stability = compute_param_stability(params_list)
        assert stability.get("fast", 0) > 0.0

    def test_empty_list(self):
        assert compute_param_stability([]) == {}


class TestValidateWfaConfig:
    def test_valid_config_passes(self):
        validate_wfa_config(n_folds=4, n_combinations=20, max_combinations=200)

    def test_exceeds_cap_raises(self):
        with pytest.raises(ValueError):
            validate_wfa_config(n_folds=10, n_combinations=30, max_combinations=200)

    def test_zero_folds_raises(self):
        with pytest.raises(ValueError):
            validate_wfa_config(n_folds=0, n_combinations=10, max_combinations=200)

    def test_zero_combos_raises(self):
        with pytest.raises(ValueError):
            validate_wfa_config(n_folds=4, n_combinations=0, max_combinations=200)

    def test_exact_cap_passes(self):
        validate_wfa_config(n_folds=10, n_combinations=20, max_combinations=200)


class TestEstimateWfaRuns:
    def test_basic_estimate(self):
        result = estimate_wfa_runs(
            start_date=date(2018, 1, 1), end_date=date(2022, 1, 1),
            in_sample_days=365, out_of_sample_days=90,
            window_type="rolling", anchored=False,
            param_grid={"fast": [3, 5, 10], "slow": [20, 30]},
        )
        assert result["n_folds"] >= 2
        assert result["n_combinations"] == 6
        assert result["total_runs"] == result["n_folds"] * result["n_combinations"]
        assert result["error"] is None

    def test_infeasible_returns_not_feasible(self):
        result = estimate_wfa_runs(
            start_date=date(2010, 1, 1), end_date=date(2024, 1, 1),
            in_sample_days=90, out_of_sample_days=30,
            window_type="rolling", anchored=False,
            param_grid={"a": list(range(20)), "b": list(range(20))},
            max_combinations=50,
        )
        assert result["feasible"] is False

    def test_invalid_config_returns_error(self):
        result = estimate_wfa_runs(
            start_date=date(2022, 1, 1), end_date=date(2022, 3, 1),
            in_sample_days=365, out_of_sample_days=90,
            window_type="rolling", anchored=False,
            param_grid={"fast": [3, 5]},
        )
        assert result["error"] is not None
        assert result["total_runs"] == 0

    def test_expanding_window(self):
        result = estimate_wfa_runs(
            start_date=date(2018, 1, 1), end_date=date(2022, 1, 1),
            in_sample_days=365, out_of_sample_days=90,
            window_type="expanding", anchored=False,
            param_grid={"fast": [3, 5]},
        )
        assert result["n_folds"] >= 2
        assert result["error"] is None

    def test_anchored_rolling(self):
        result = estimate_wfa_runs(
            start_date=date(2018, 1, 1), end_date=date(2022, 1, 1),
            in_sample_days=365, out_of_sample_days=90,
            window_type="rolling", anchored=True,
            param_grid={"fast": [3, 5]},
        )
        assert result["n_folds"] >= 2
        assert result["error"] is None
