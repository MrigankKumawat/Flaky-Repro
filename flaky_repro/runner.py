import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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


def find_next_investigation_number(
    folder: str, prefix: str = "investigation"
) -> str:
    """Finds the highest existing file number in folder and returns the next filename."""
    if not os.path.exists(folder):
        return f"{prefix}_001.json"

    existing_numbers = []
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.json$")

    for filename in os.listdir(folder):
        match = pattern.match(filename)
        if match:
            existing_numbers.append(int(match.group(1)))

    next_num = max(existing_numbers) + 1 if existing_numbers else 1
    return f"{prefix}_{next_num:03d}.json"


def run_single_test(target_test: str, run_index: int, timing_delay = 0) -> dict:

    if timing_delay > 0:
        time.sleep(timing_delay)
    
    res = subprocess.run(
        ["pytest", target_test], capture_output=True, text=True
    )

    if res.returncode == 0:
        return {"run_index": run_index, "passed": True, "evidence": None}

    line_num = "Unknown"
    assertion_text = "No assertion isolated."

    for line in res.stdout.splitlines():

        clean_line = line.strip()

        if clean_line.startswith("E ") and "assert" in clean_line:
            assertion_text = re.sub(r"^E\s+assert\s*", "", clean_line).strip()

        match = re.search(r"\.py:(\d+): AssertionError", clean_line)

        if match:
            line_num = match.group(1)

    return {
        "run_index": run_index,
        "passed": False,
        "evidence": {
            "run_index": run_index,
            "line": line_num,
            "assertion": assertion_text,
        },
    }


def run_sequential_test(target_test: str, runs: int, timing_delay):
    passed = 0
    failed = 0
    failure_evidence = []

    for i in range(1, runs + 1):
        res = run_single_test(target_test, i, timing_delay)
        if res["passed"]:
            passed += 1
        else:
            failed += 1
            failure_evidence.append(res["evidence"])

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


def json_experiments(result, runs, mode, target_test, workers):
    folder = "results"
    os.makedirs(folder, exist_ok=True)

    if mode == "Sequential":
        summary_sequential = result
        extracted_numbers = []
        for ev in summary_sequential["evidence"]:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", ev["assertion"])
            if nums:
                extracted_numbers.append(float(nums[0]))

        min_val_sequential = (
            min(extracted_numbers) if extracted_numbers else None
        )
        max_val_sequential = (
            max(extracted_numbers) if extracted_numbers else None
        )

        sequential = {
            "test": {
                "path": target_test,
                # "name":name
            },
            "configuration": {
                "runs": runs,
                "mode": mode,
                "workers": workers,
            },
            "summary": {
                "total_runs": summary_sequential["total_runs"],
                "passed": summary_sequential["passed"],
                "failed": summary_sequential["failed"],
                "failure_rate": summary_sequential["failure_rate"],
                "classification": summary_sequential["rate_classification"],
            },
            "failure_evidence": {
                "failing_line": (
                    summary_sequential["evidence"][0]["line"]
                    if summary_sequential["evidence"]
                    else None
                ),
                "assertion": (
                    summary_sequential["evidence"][0]["assertion"]
                    if summary_sequential["evidence"]
                    else None
                ),
                "observed_min": round(min_val_sequential, 2) if min_val_sequential is not None else None,
                "observed_max": round(max_val_sequential, 2) if max_val_sequential is not None else None,
            },  
        }

        next_file = find_next_investigation_number(folder, "investigation")
        filepath = os.path.join(folder, next_file)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(sequential, f, indent=4)

    if mode == "Parallel":
        summary_parallel = result
        extracted_numbers = []
        for ev in summary_parallel["evidence"]:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", ev["assertion"])
            if nums:
                extracted_numbers.append(float(nums[0]))

        min_val_parallel = min(extracted_numbers) if extracted_numbers else None
        max_val_parallel = max(extracted_numbers) if extracted_numbers else None

        parallel = {
            "test": {
                "path": target_test,
                # "name":name
            },
            "configuration": {
                "runs": runs,
                "mode": mode,
                "workers": workers,
            },
            "summary": {
                "total_runs": summary_parallel["total_runs"],
                "passed": summary_parallel["passed"],
                "failed": summary_parallel["failed"],
                "failure_rate": summary_parallel["failure_rate"],
                "classification": summary_parallel["rate_classification"],
            },
            "failure_evidence": {
                "failing_line": (
                    summary_parallel["evidence"][0]["line"]
                    if summary_parallel["evidence"]
                    else None
                ),
                "assertion": (
                    summary_parallel["evidence"][0]["assertion"]
                    if summary_parallel["evidence"]
                    else None
                ),
                "observed_min": round(min_val_parallel, 2) if min_val_parallel is not None else None,
                "observed_max": round(max_val_parallel, 2) if max_val_parallel is not None else None,
            },
        }

        next_file = find_next_investigation_number(folder, "investigation")
        filepath = os.path.join(folder, next_file)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(parallel, f, indent=4)


def run_parallel_test(target_test: str, runs: int, max_workers: int = 4, timing_delay: float = 0.0):
    passed = 0
    failed = 0
    failure_evidence = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [
            executor.submit(run_single_test, target_test, i, timing_delay)
            for i in range(1, runs + 1)
        ]

        for future in as_completed(futures):

            res = future.result()

            if res["passed"]:
                passed += 1

            else:
                failed += 1
                failure_evidence.append(res["evidence"])

    failure_evidence.sort(key=lambda x: x["run_index"])

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
