from flaky_repro.runner import run_sequential_test
from flaky_repro.experiment_engine import run_initial_investigation
from flaky_repro.candidate_engine import (
    normalize_investigation,
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


def run_pipeline(
    target_test: str,
    runs: int,
    investigation_mode: str,
    investigation_workers: list,
    investigation_timing_delays: list,
    top_n: int = 3,
    repeated_runs: int = 3,
    reproduction_runs: int = 3,
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
    baseline_result = run_sequential_test(target_test, runs, timing_delay=0)

    # ---- INVESTIGATION -------------------------------------------------
    investigation_result = run_initial_investigation(
        target_test=target_test,
        runs=runs,
        mode=investigation_mode,
        workers_count=investigation_workers,
        timing_delay=investigation_timing_delays,
    )

    # ---- CANDIDATE PREPARATION -----------------------------------------
    raw_candidates = normalize_investigation(investigation_result)

    # ---- CANDIDATE VALIDATION -------------------------------------------
    validation_report = []
    valid_candidates = []
    for candidate in raw_candidates:
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
    for candidate in top_candidates:
        repeated_result = run_candidate_repetitions(
            candidate,
            target_test,
            runs,
            repeated_runs,
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
    print("\n" + "=" * 60)
    print("        DEBUG: CANDIDATE CONFIRMATION DETAILS")
    print("=" * 60)

    for record in candidate_confirmations:

        print("\n" + "-" * 60)

        print("CANDIDATE:")
        print(record["candidate"])

        print("\nREPEATED ANALYSIS:")
        print(record["repeated_analysis"])

        print("\nCONFIRMATION:")
        print(record["confirmation"])
    # ---- REPRODUCTION / REPRODUCTION ANALYSIS / CLASSIFICATION -------------
    # Only candidates that were CONFIRMED get reproduced.
    candidate_reproductions = []
    for confirmation_record in confirmed_candidates:
        candidate = confirmation_record["candidate"]

        reproduction_result = run_reproduction(
            candidate,
            target_test,
            runs,
            reproduction_runs,
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

    target_test = "examples/test_timing_flaky.py::test_timing_behavior"

    result = run_pipeline(
        target_test=target_test,
        runs=5,

        investigation_mode="Parallel",
        investigation_workers=[2, 4, 8],
        investigation_timing_delays=[10, 20],

        top_n=3,

        repeated_runs=3,
        reproduction_runs=3,

        repetition_mode="Parallel",
        repetition_workers=4,
    )

    print("\n" + "=" * 60)
    print("             FLAKY-REPRO PIPELINE TEST")
    print("=" * 60)

    print("\n--- TEST ---")
    print(f"Target : {result['target_test']}")

    print("\n--- BASELINE ---")
    print(result["baseline"])

    print("\n--- CANDIDATES ---")
    print(f"Raw       : {len(result['candidates']['raw'])}")
    print(f"Valid     : {len(result['candidates']['valid'])}")
    print(f"Ranked    : {len(result['candidates']['ranked'])}")
    print(f"Top       : {len(result['candidates']['top'])}")

    print("\n--- CONFIRMATIONS ---")

    for record in result["candidate_confirmations"]:

        candidate = record["candidate"]
        confirmation = record["confirmation"]

        print(
            f"{candidate['type']} "
            f"{candidate['condition']} "
            f"→ {confirmation['classification']}"
        )

    print("\n--- CONFIRMED CANDIDATES ---")

    for record in result["confirmed_candidates"]:

        candidate = record["candidate"]

        print(
            f"{candidate['type']} "
            f"{candidate['condition']}"
        )

    print("\n--- REPRODUCTIONS ---")

    for record in result["candidate_reproductions"]:

        candidate = record["candidate"]
        classification = record["reproduction_classification"]

        print(
            f"{candidate['type']} "
            f"{candidate['condition']} "
            f"→ {classification['classification']}"
        )

    print("\n" + "=" * 60)
    print("           PIPELINE TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()