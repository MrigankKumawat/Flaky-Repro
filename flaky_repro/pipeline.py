from flaky_repro.runner import run_sequential_test
from flaky_repro.experiment_engine import run_initial_investigation
from flaky_repro.candidate_engine import (
    normalize_investigation,
    deduplicate_candidates,
    validate_candidate,
    build_rankable_candidates,
    rank_candidates,
    select_top_candidates,
    run_candidate_repetitions,
    analyze_repeated_candidate,
    confirm_candidate,
)
from flaky_repro.reproduction_engine import (
    run_reproduction,
    analyze_reproduction,
    classify_reproduction,
)
from flaky_repro.formatting import print_pipeline_result


def run_pipeline(
    target_test: str,
    baseline_runs: int,
    investigation_runs: int,
    confirmation_runs: int,
    reproduction_runs: int,
    investigation_mode: str,
    investigation_workers: list,
    investigation_timing_delays: list,
    top_n: int = 3,
    confirmation_repetitions: int = 3,
    reproduction_repetitions: int = 3,
    repetition_mode: str = "Parallel",
    repetition_workers: int = 4,
):
    """
    Thin orchestration layer for the Flaky-Repro project.

    This function ONLY calls existing engine functions and passes their
    outputs to the next existing function. No experiment, comparison,
    candidate, reproduction, or classification logic lives here.
    """

    # ---- BASELINE ----------------------------------------------------
    print("\nRunning Baseline...")
    baseline_result = run_sequential_test(target_test, baseline_runs, timing_delay=0)

    # ---- INVESTIGATION -------------------------------------------------
    print("\nRunning Investigation...")
    investigation_result = run_initial_investigation(
        target_test=target_test,
        runs=investigation_runs,
        mode=investigation_mode,
        workers_count=investigation_workers,
        timing_delay=investigation_timing_delays,
        sequential_result=baseline_result
    )

    # ---- CANDIDATE PREPARATION -----------------------------------------
    raw_candidates = normalize_investigation(
        investigation_result,
        investigation_mode,
        investigation_workers[0]
    )

    # ---- CANDIDATE CANONICALIZATION / DEDUPLICATION ---------------------
    # Equivalent execution configurations produced by different experiment
    # types (e.g. Worker(4 workers) and Mode(Parallel, 4 workers)) are
    # collapsed to a single candidate here, before validation/ranking, so
    # they are not counted as independent evidence.
    deduplicated_candidates = deduplicate_candidates(raw_candidates)

    # ---- CANDIDATE VALIDATION -------------------------------------------
    validation_report = []
    valid_candidates = []
    for candidate in deduplicated_candidates:
        validation = validate_candidate(candidate)
        validation_report.append({"candidate": candidate, "validation": validation})
        if validation["valid"]:
            valid_candidates.append(candidate)

    # ---- CANDIDATE CLASSIFICATION (pre-ranking prep) --------------------
    prepared_candidates = build_rankable_candidates(baseline_result, valid_candidates)

    # ---- CANDIDATE RANKING ----------------------------------------------
    ranked_candidates = rank_candidates(prepared_candidates)

    # ---- TOP CANDIDATE SELECTION -----------------------------------------
    top_candidates = select_top_candidates(ranked_candidates, count=top_n)

    # ---- REPEATED CANDIDATE ANALYSIS / CONFIRMATION -----------------------
    candidate_confirmations = []
    confirmed_candidates = []
    if top_candidates:
        print("\nRunning Candidate Repetitions...")
    for candidate in top_candidates:
        repeated_result = run_candidate_repetitions(
            candidate,
            target_test,
            confirmation_runs,
            confirmation_repetitions,
            repetition_mode,
            repetition_workers,
        )
        repeated_analysis = analyze_repeated_candidate(baseline_result, repeated_result)
        confirmation = confirm_candidate(repeated_analysis)

        confirmation_record = {
            "candidate": candidate,
            "repeated_result": repeated_result,
            "repeated_analysis": repeated_analysis,
            "confirmation": confirmation,
        }
        candidate_confirmations.append(confirmation_record)

        if confirmation["classification"] == "Confirmed":
            confirmed_candidates.append(confirmation_record)
    # ---- REPRODUCTION / REPRODUCTION ANALYSIS / CLASSIFICATION -------------
    # Only candidates that were CONFIRMED get reproduced.
    candidate_reproductions = []
    if confirmed_candidates:
        print("\nRunning Reproductions...")
    for confirmation_record in confirmed_candidates:
        candidate = confirmation_record["candidate"]

        reproduction_result = run_reproduction(
            candidate,
            target_test,
            reproduction_runs,
            reproduction_repetitions,
            repetition_mode,
            repetition_workers,
        )
        reproduction_analysis = analyze_reproduction(baseline_result, reproduction_result)
        reproduction_classification = classify_reproduction(reproduction_analysis)

        candidate_reproductions.append({
            "candidate": candidate,
            "reproduction_result": reproduction_result,
            "reproduction_analysis": reproduction_analysis,
            "reproduction_classification": reproduction_classification,
        })

    # ---- FINAL RESULT ------------------------------------------------------
    return {
        "target_test": target_test,
        "baseline": baseline_result,
        "investigation": investigation_result,
        "candidates": {
            "raw": raw_candidates,
            "deduplicated": deduplicated_candidates,
            "validation": validation_report,
            "valid": valid_candidates,
            "prepared": prepared_candidates,
            "ranked": ranked_candidates,
            "top": top_candidates,
        },
        "candidate_confirmations": candidate_confirmations,
        "confirmed_candidates": confirmed_candidates,
        "candidate_reproductions": candidate_reproductions,
    }

def main():
    import sys

    version_str = "flaky-repro 0.1.0"
    help_text = """Usage: flaky-repro [OPTIONS] <pytest-target>

An empirical, frequency-based flaky test diagnosis and reproduction tool.

Options:
  -h, --help      Show this usage message and exit.
  -V, --version   Show the version and exit.

Arguments:
  <pytest-target> The pytest target test to run (e.g. tests/test_concurrency.py::test_sensitive).
"""

    if len(sys.argv) < 2:
        print("Error: Missing target test.", file=sys.stderr)
        print(help_text, file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]

    if arg in ("-h", "--help"):
        print(help_text)
        sys.exit(0)

    if arg in ("-V", "--version"):
        print(version_str)
        sys.exit(0)

    target_test = arg

    result = run_pipeline(
        target_test=target_test,
        baseline_runs=20,
        investigation_runs=20,
        confirmation_runs=20,
        reproduction_runs=40,

        investigation_mode="Parallel",
        investigation_workers=[2, 4, 8],
        investigation_timing_delays=[10, 20],

        top_n=3,

        confirmation_repetitions=3,
        reproduction_repetitions=3,

        repetition_mode="Parallel",
        repetition_workers=4,
    )

    print_pipeline_result(result)

if __name__ == "__main__":
    main()