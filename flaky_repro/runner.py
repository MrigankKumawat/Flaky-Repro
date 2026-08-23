import os
import re
import sys
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


def draw_progress_bar(completed, total, prefix=""):
    percent = (completed / total) * 100
    filled_length = int(20 * completed // total)
    bar = '=' * filled_length + '-' * (20 - filled_length)
    sys.stdout.write(f"\r{prefix:<25} [{bar}] {percent:.0f}% ({completed}/{total})")
    sys.stdout.flush()
    if completed == total:
        sys.stdout.write("\n")
        sys.stdout.flush()





def run_single_test(
    target_test: str,
    run_index: int,
    timing_delay=0,
    timeout: int = 60
) -> dict:

    if timing_delay > 0:
        time.sleep(timing_delay)

    try:
        res = subprocess.run(
            [sys.executable, "-m", "pytest", target_test],
            capture_output=True,
            text=True,
            timeout=timeout
        )

    except subprocess.TimeoutExpired:
        return {
            "run_index": run_index,
            "passed": False,
            "evidence": {
                "run_index": run_index,
                "line": "Unknown",
                "assertion": (
                    f"Test execution timed out after "
                    f"{timeout} seconds."
                ),
                "error_type": "Timeout",
                "stderr": None
            }
        }

    if res.returncode == 0:
        return {
            "run_index": run_index,
            "passed": True,
            "evidence": None
        }

    stdout = res.stdout or ""
    stderr = res.stderr or ""

    line_num = "Unknown"
    assertion_text = "No assertion isolated."
    error_type = "TestFailure"

    # ------------------------------------------------------------
    # Extract exception type from pytest output
    # ------------------------------------------------------------
    exception_patterns = [
        r"E\s+([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))(?::|$)",
        r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):"
    ]

    for pattern in exception_patterns:
        match = re.search(pattern, stdout)

        if match:
            error_type = match.group(1)
            break

    # ------------------------------------------------------------
    # Extract source line
    # ------------------------------------------------------------
    for line in stdout.splitlines():

        clean_line = line.strip()

        match = re.search(
            r"\.py:(\d+):",
            clean_line
        )

        if match:
            line_num = match.group(1)
            break

    # ------------------------------------------------------------
    # Extract assertion / error message
    # ------------------------------------------------------------
    evidence_lines = []

    for line in stdout.splitlines():

        clean_line = line.strip()

        if clean_line.startswith("E "):
            evidence_lines.append(
                re.sub(r"^E\s+", "", clean_line)
            )

    if evidence_lines:
        assertion_text = "\n".join(evidence_lines)

    # ------------------------------------------------------------
    # If stdout did not contain useful evidence,
    # preserve stderr instead.
    # ------------------------------------------------------------
    if (
        assertion_text == "No assertion isolated."
        and stderr.strip()
    ):
        assertion_text = stderr.strip()

    # ------------------------------------------------------------
    # Final structured failure result
    # ------------------------------------------------------------
    return {
        "run_index": run_index,
        "passed": False,
        "evidence": {
            "run_index": run_index,
            "line": line_num,
            "assertion": assertion_text,
            "error_type": error_type,
            "stderr": stderr if stderr.strip() else None
        }
    }


def run_sequential_test(target_test: str, runs: int, timing_delay):
    passed = 0
    failed = 0
    failure_evidence = []

    if timing_delay > 0:
        prefix = f"Seq Delay {int(timing_delay * 1000)}ms"
    else:
        prefix = "Seq Baseline"

    for i in range(1, runs + 1):
        res = run_single_test(target_test, i, timing_delay)
        if res["passed"]:
            passed += 1
        else:
            failed += 1
            failure_evidence.append(res["evidence"])
        draw_progress_bar(i, runs, prefix)

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





def run_parallel_test(target_test: str, runs: int, max_workers: int = 4, timing_delay: float = 0.0):
    passed = 0
    failed = 0
    failure_evidence = []

    if timing_delay > 0:
        prefix = f"Par Delay {int(timing_delay * 1000)}ms ({max_workers}w)"
    else:
        prefix = f"Parallel ({max_workers} workers)"

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [
            executor.submit(run_single_test, target_test, i, timing_delay)
            for i in range(1, runs + 1)
        ]

        completed = 0
        for future in as_completed(futures):

            res = future.result()

            if res["passed"]:
                passed += 1

            else:
                failed += 1
                failure_evidence.append(res["evidence"])

            completed += 1
            draw_progress_bar(completed, runs, prefix)

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
