from flaky_repro.runner import run_sequential_test
from flaky_repro.runner import run_parallel_test
from flaky_repro.runner import json_experiments
import re

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

    test_name = (
        target_test.split("::")[-1] if "::" in target_test else target_test
    )

    json_experiments(result, runs, mode_label, target_test, workers)

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