import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

def classify_flakiness(failure_rate: float) -> str:
    if failure_rate == 0.0:
        return "Stable"
    elif failure_rate <= 20.0:
        return "Low Flakiness"
    elif failure_rate <= 50.0:
        return "Flaky/Moderate"
    elif failure_rate <= 80.0:
        return "Highly Flaky"
    elif failure_rate < 100.0:
        return "Severely Unstable"
    return "Consistently Failing"


def run_single_test(target_test: str, run_index: int) -> dict:

    res = subprocess.run(
        ["pytest", target_test],
        capture_output=True,
        text=True
    )

    if res.returncode == 0:
        return {
            "run_index": run_index,
            "passed": True,
            "evidence": None
        }

    line_num = "Unknown"
    assertion_text = "No assertion isolated."

    for line in res.stdout.splitlines():

        clean_line = line.strip()

        if clean_line.startswith("E ") and "assert" in clean_line:
            assertion_text = re.sub(
                r"^E\s+assert\s*",
                "",
                clean_line
            ).strip()

        match = re.search(
            r"\.py:(\d+): AssertionError",
            clean_line
        )

        if match:
            line_num = match.group(1)

    return {
        "run_index": run_index,
        "passed": False,
        "evidence": {
            "run_index": run_index,
            "line": line_num,
            "assertion": assertion_text
        }
    }


def run_sequential_test(target_test: str, runs: int):
    passed = 0
    failed = 0 
    failure_evidence = []
    
    for i in range(1, runs+1):
        res = run_single_test(target_test, i)
        if res['passed']:
            passed += 1
        else:
            failed += 1
            failure_evidence.append(res['evidence'])
        
    for count, item in enumerate(failure_evidence, start=1):
        item["failure_count"] = count

    failure_rate = (failed / runs) * 100 if runs > 0 else 0.0

    return {
        "total_runs": runs,
        "passed": passed,
        "failed": failed,
        "failure_rate": round(failure_rate, 2),
        "rate_classification": classify_flakiness(failure_rate),
        "evidence": failure_evidence,
    }
        

def run_parallel_test(target_test: str, runs: int, max_workers: int = 4):

    passed = 0
    failed = 0
    failure_evidence = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [
            executor.submit(
                run_single_test,
                target_test,
                i
            )
            for i in range(1, runs + 1)
        ]

        for future in as_completed(futures):

            res = future.result()

            if res["passed"]:
                passed += 1

            else:
                failed += 1
                failure_evidence.append(res["evidence"])

    failure_evidence.sort(
        key=lambda x: x["run_index"]
    )

    for count, item in enumerate(
        failure_evidence,
        start=1
    ):
        item["failure_count"] = count

    failure_rate = (
        (failed / runs) * 100
        if runs > 0
        else 0.0
    )

    return {
        "total_runs": runs,
        "passed": passed,
        "failed": failed,
        "failure_rate": round(failure_rate, 2),
        "rate_classification": classify_flakiness(
            failure_rate
        ),
        "evidence": failure_evidence
    }


if __name__ == "__main__":
    target_test = input("Enter test file path: ").strip()
    runs = int(input("Enter number of test runs: ").strip())
    mode = int(input("Select 1 for Sequential and 2 for Parallel: ").strip())
    
    workers = None
    if mode == 1:
        mode_label = "Sequential"
        result = run_sequential_test(target_test, runs)
    elif mode == 2:
        workers = int(input("Enter number of workers: ").strip())
        mode_label = "Parallel"
        result = run_parallel_test(target_test, runs, workers)
    else:
        print("Invalid selection.")
        exit(1)

    test_name = target_test.split("::")[-1] if "::" in target_test else target_test

    # Clean Final Summary Report
    print("\n============= FLAKY-REPRO =============")
    print(f"\nTest:           {test_name}")
    print(f"Mode:           {mode_label}")
    if workers:
        print(f"Workers:        {workers}")
    print(f"Runs:           {runs}")

    print("\n--------------- SUMMARY ----------------\n")
    print(f"Passed:         {result['passed']}")
    print(f"Failed:         {result['failed']}")
    print(f"Failure Rate:   {result['failure_rate']}%")
    print(f"\nClassification: {result['rate_classification']}")

    if result["evidence"]:
        # Extract sample line and assertion
        failing_line = result["evidence"][0]["line"]
        assertion_sample = result["evidence"][0]["assertion"]

        # Parse observed numeric range if comparisons are present
        extracted_numbers = []
        for ev in result["evidence"]:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", ev["assertion"])
            if nums:
                extracted_numbers.append(float(nums[0]))

        print("\n----------- FAILURE PATTERN ------------\n")
        print(f"Failing Line:       {failing_line}")
        print(f"Assertion:          {assertion_sample}")

        if extracted_numbers:
            min_val = min(extracted_numbers)
            max_val = max(extracted_numbers)
            print(f"\nObserved Range:     {min_val:.3f}s - {max_val:.3f}s")

        print("\n-----------------------------------------")
        print("\nLikely Pattern:")
        print("Timing-sensitive failure")
        print("\n-----------------------------------------")