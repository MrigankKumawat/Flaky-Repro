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
    execution_config: dict,
    run_index: int
) -> dict:
    """
    Execute one test once using an ExecutionConfig.

    This layer handles only actual test execution and individual
    run-result/evidence extraction.
    """

    target_test = execution_config["target_test"]
    timing_delay = execution_config.get("timing_delay", 0)
    timeout = execution_config.get("timeout", 60)

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

    exception_patterns = [
        r"E\s+([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))(?::|$)",
        r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):"
    ]

    for pattern in exception_patterns:
        match = re.search(pattern, stdout)

        if match:
            error_type = match.group(1)
            break

    for line in stdout.splitlines():
        clean_line = line.strip()

        match = re.search(r"\.py:(\d+):", clean_line)

        if match:
            line_num = match.group(1)
            break

    evidence_lines = []

    for line in stdout.splitlines():
        clean_line = line.strip()

        if clean_line.startswith("E "):
            evidence_lines.append(
                re.sub(r"^E\s+", "", clean_line)
            )

    if evidence_lines:
        assertion_text = "\n".join(evidence_lines)

    if (
        assertion_text == "No assertion isolated."
        and stderr.strip()
    ):
        assertion_text = stderr.strip()

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


def _build_execution_result(
    run_results: list[dict],
    total_runs: int
) -> dict:
    """Aggregate individual run results."""

    passed = sum(
        1 for result in run_results
        if result["passed"]
    )
    failed = total_runs - passed

    failure_evidence = [
        result["evidence"]
        for result in run_results
        if not result["passed"]
    ]

    failure_evidence.sort(
        key=lambda item: item["run_index"]
    )

    for count, item in enumerate(
        failure_evidence,
        start=1
    ):
        item["failure_count"] = count

    failure_rate = (
        (failed / total_runs) * 100
        if total_runs > 0
        else 0.0
    )

    return {
        "total_runs": total_runs,
        "passed": passed,
        "failed": failed,
        "failure_rate": round(failure_rate, 2),
        "rate_classification": classify_flakiness(
            failure_rate
        ),
        "evidence": failure_evidence,
    }


def run_sequential_test(execution_config: dict) -> dict:
    """Execute a test repeatedly in sequential mode."""

    runs = execution_config["runs"]
    timing_delay = execution_config.get(
        "timing_delay",
        0
    )

    if timing_delay > 0:
        prefix = (
            f"Seq Delay "
            f"{int(timing_delay * 1000)}ms"
        )
    else:
        prefix = "Seq Baseline"

    run_results = []

    for i in range(1, runs + 1):
        result = run_single_test(
            execution_config,
            i
        )
        run_results.append(result)

        draw_progress_bar(
            i,
            runs,
            prefix
        )

    return _build_execution_result(
        run_results,
        runs
    )


def run_parallel_test(execution_config: dict) -> dict:
    """Execute a test repeatedly in parallel mode."""

    runs = execution_config["runs"]
    workers = execution_config["workers"]
    timing_delay = execution_config.get(
        "timing_delay",
        0
    )

    if timing_delay > 0:
        prefix = (
            f"Par Delay "
            f"{int(timing_delay * 1000)}ms "
            f"({workers}w)"
        )
    else:
        prefix = (
            f"Parallel "
            f"({workers} workers)"
        )

    run_results = []

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:

        futures = [
            executor.submit(
                run_single_test,
                execution_config,
                i
            )
            for i in range(1, runs + 1)
        ]

        completed = 0

        for future in as_completed(futures):
            result = future.result()
            run_results.append(result)

            completed += 1

            draw_progress_bar(
                completed,
                runs,
                prefix
            )

    return _build_execution_result(
        run_results,
        runs
    )


def run_test(execution_config: dict) -> dict:
    """
    Main runner entry point.

    Dispatch execution based on execution_config["mode"].
    """

    mode = execution_config["mode"]

    if mode == "Sequential":
        return run_sequential_test(
            execution_config
        )

    if mode == "Parallel":
        return run_parallel_test(
            execution_config
        )

    raise ValueError(
        f"Unsupported execution mode: {mode}"
    )

