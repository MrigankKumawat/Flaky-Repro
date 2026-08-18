from flaky_repro.runner import run_sequential_test
from flaky_repro.runner import run_parallel_test
from flaky_repro.comparison_engine import compare_results
from flaky_repro.comparison_engine import compare_repeated_observations
from flaky_repro.comparison_engine import extract_effects
from flaky_repro.comparison_engine import analyze_consistency
from flaky_repro.comparison_engine import build_evidence_summary


def run_repeated_experiment(target_test:str, runs:int, mode:str, workers:int, repeat_count = None):
    all_results = []
    if mode == "Sequential":
        if repeat_count is None:
            for i in range(0,4):
                result = run_sequential_test(target_test, runs, timing_delay=0)
                all_results.append(result)
        else:
            for i in range(0, repeat_count):
                result = run_sequential_test(target_test, runs, timing_delay=0)
                all_results.append(result)
    elif mode == "Parallel":
        if repeat_count is None:
            for i in range(0,4):
                result = run_parallel_test(target_test, runs, max_workers=workers, timing_delay=0)
                all_results.append(result)
        else:
            for i in range(0, repeat_count):
                result = run_parallel_test(target_test, runs, max_workers=workers, timing_delay=0)
                all_results.append(result)

    return all_results

def run_investigation(
    target_test: str,
    runs: int,
    mode: str,
    workers: int,
    repeat_count: int = 3
):
     
    baseline_result = run_sequential_test(target_test, runs, timing_delay=0)

    if mode == "Sequential":
        experiment_result = run_sequential_test(target_test, runs, timing_delay=0)
    elif mode == "Parallel":
        experiment_result = run_parallel_test(target_test, runs, workers, timing_delay=0)

    compare_baseline_experiment = compare_results(baseline_results=baseline_result, experiment_results=experiment_result)

    repeated_experiment = run_repeated_experiment(target_test, runs, mode, workers, repeat_count)

    compare_repeated = compare_repeated_observations(baseline_result, repeated_experiment)

    effects = extract_effects(compare_repeated)

    consistency_analyze = analyze_consistency(effects)

    evidence_summary = build_evidence_summary(
        comparison_result=compare_baseline_experiment["comparison"],
        consistency_result=consistency_analyze
    )

    return {
        "baseline": baseline_result,
        "experiment": experiment_result,
        "comparison": compare_baseline_experiment,
        "repeated_observations": repeated_experiment,
        "repeated_comparisons": compare_repeated,
        "effects": effects,
        "consistency": consistency_analyze,
        "evidence": evidence_summary
    }

if __name__ == "__main__":
    target_test = input("Enter test file path: ").strip()
    runs = int(input("Enter number of runs: ").strip())
    workers = int(input("Enter workers: ").strip())

    result = run_investigation(
        target_test=target_test,
        runs=runs,
        mode="Parallel",
        workers=workers,
        repeat_count=3
    )

    comparison = result["comparison"]["comparison"]
    consistency = result["consistency"]

    print("\n")
    print("=" * 60)
    print("              FLAKY-REPRO INVESTIGATION")
    print("=" * 60)

    print("\nTEST")
    print("-" * 60)
    print(f"Target       : {target_test}")
    print(f"Runs         : {runs}")
    print(f"Mode         : Parallel")
    print(f"Workers      : {workers}")

    baseline = result["baseline"]
    experiment = result["experiment"]

    print("\nBASELINE")
    print("-" * 60)
    print(f"Passed       : {baseline['passed']}")
    print(f"Failed       : {baseline['failed']}")
    print(f"Failure Rate : {baseline['failure_rate']}%")

    print("\nEXPERIMENT")
    print("-" * 60)
    print(f"Passed       : {experiment['passed']}")
    print(f"Failed       : {experiment['failed']}")
    print(f"Failure Rate : {experiment['failure_rate']}%")

    print("\nCOMPARISON")
    print("-" * 60)
    print(f"Failure Δ    : {comparison['failure_rate_delta']} percentage points")
    print(f"Relative Δ   : {comparison['relative_change']}%")
    print(f"Direction    : {comparison['direction']}")

    print("\nREPEATED EFFECTS")
    print("-" * 60)
    print(f"Observations : {consistency['observation_count']}")
    print(f"Effects      : {result['effects']}")

    print("\nCONSISTENCY")
    print("-" * 60)
    print(f"Mean Effect  : {consistency['mean_effect']} pp")
    print(f"Min Effect   : {consistency['min_effect']} pp")
    print(f"Max Effect   : {consistency['max_effect']} pp")
    print(f"Effect Range : {consistency['effect_range']} pp")
    print(f"Std Dev      : {consistency['standard_deviation']}")
    print(f"CV           : {consistency['coefficient_variation']}")

    print("\nEVIDENCE SUMMARY")
    print("-" * 60)
    print(f"Effect       : {comparison['direction']}")
    print(f"Mean Effect  : {consistency['mean_effect']} pp")
    print(f"Consistency  : CV = {consistency['coefficient_variation']}")

    print("\n" + "=" * 60)
    print("          INVESTIGATION DATA COLLECTED")
    print("=" * 60)