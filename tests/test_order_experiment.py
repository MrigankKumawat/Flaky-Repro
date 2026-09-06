from flaky_repro.experiment_engine import order_experiment


TARGET_TEST = (
    "flaky_repro/examples/functional_validation/test_order_state.py"
    "::test_target_depends_on_state"
)

SETUP_TEST = (
    "flaky_repro/examples/functional_validation/test_order_state.py"
    "::test_setup_changes_state"
)


def test_order_experiment():
    runs = 3

    sequences = [
        # Target runs alone → should PASS
        [TARGET_TEST],

        # Setup changes shared state immediately before target → should FAIL
        [SETUP_TEST, TARGET_TEST],
    ]

    results = order_experiment(
        target_test=TARGET_TEST,
        runs=runs,
        sequences=sequences,
    )

    assert len(results) == 2

    # --------------------------------------------------
    # Target alone
    # --------------------------------------------------

    alone_result = results[0]["result"]

    assert alone_result["total_runs"] == runs
    assert alone_result["passed"] == runs
    assert alone_result["failed"] == 0
    assert alone_result["unknown"] == 0
    assert alone_result["failure_rate"] == 0.0

    # --------------------------------------------------
    # Setup → target
    # --------------------------------------------------

    ordered_result = results[1]["result"]

    assert ordered_result["total_runs"] == runs
    assert ordered_result["passed"] == 0
    assert ordered_result["failed"] == runs
    assert ordered_result["unknown"] == 0
    assert ordered_result["failure_rate"] == 100.0