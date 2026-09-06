from flaky_repro.runner import run_test, run_sequence_test
from flaky_repro.experiment_engine import (
    worker_experiment,
    timing_experiment,
    mode_experiment,
    timeout_experiment,
    order_experiment,
)


TARGET = "flaky_repro/examples/functional_validation/test_timing_flaky.py::test_timing_behavior"


def assert_result_shape(result):
    assert "total_runs" in result
    assert "passed" in result
    assert "failed" in result
    assert "unknown" in result
    assert "failure_rate" in result
    assert "rate_classification" in result
    assert "evidence" in result

    assert result["passed"] + result["failed"] + result["unknown"] == result["total_runs"]


def test_sequential_runner():
    result = run_test({
        "target_test": TARGET,
        "runs": 5,
        "timing_delay": 0,
        "timeout": 10,
        "mode": "Sequential",
        "workers": None,
    })

    assert_result_shape(result)


def test_parallel_runner():
    result = run_test({
        "target_test": TARGET,
        "runs": 5,
        "timing_delay": 0,
        "timeout": 10,
        "mode": "Parallel",
        "workers": 2,
    })

    assert_result_shape(result)


def test_worker_experiment():
    results = worker_experiment(
        target_test=TARGET,
        runs=3,
        timing_delay=0,
        timeout=10,
        mode="Parallel",
        workers_count=[2, 4],
    )

    assert len(results) == 2

    for item in results:
        assert item["worker"] in [2, 4]
        assert_result_shape(item["result"])


def test_timing_experiment():
    results = timing_experiment(
        target_test=TARGET,
        runs=3,
        mode="Parallel",
        workers_count=2,
        timing_delay=[10, 20],
        timeout=10,
    )

    assert len(results) == 2

    for item in results:
        assert item["timing_delay"] in [10, 20]
        assert_result_shape(item["result"])


def test_mode_experiment():
    results = mode_experiment(
        target_test=TARGET,
        runs=3,
        timing_delay=0,
        timeout=10,
        mode="Parallel",
        workers_count=2,
    )

    assert len(results) == 2

    assert results[0]["mode"] == "Sequential"
    assert results[1]["mode"] == "Parallel"

    for item in results:
        assert_result_shape(item["result"])


def test_timeout_experiment():
    results = timeout_experiment(
        target_test=TARGET,
        runs=3,
        timing_delay=0,
        timeout_values=[5, 10],
        mode="Parallel",
        workers_count=2,
    )

    assert len(results) == 2

    for item in results:
        assert item["timeout"] in [5, 10]
        assert_result_shape(item["result"])


def test_invalid_mode():
    try:
        run_test({
            "target_test": TARGET,
            "runs": 1,
            "timing_delay": 0,
            "timeout": 10,
            "mode": "InvalidMode",
            "workers": 2,
        })
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for invalid mode")