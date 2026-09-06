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
            "status": "UNKNOWN",  
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
            "status": "PASSED",
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
        "status": "FAILED",
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

    passed = 0
    failed = 0
    unknown = 0
    failure_evidence = []

    for result in run_results:
        if result['status'] == "PASSED":
            passed += 1
        elif result['status'] == "FAILED":
            failed += 1
            failure_evidence.append(result['evidence'])
        elif result['status'] == "UNKNOWN":
            unknown += 1

    known_runs = passed + failed
    if known_runs > 0:
        failure_rate = (failed / known_runs) * 100 if known_runs else None
        rate_classification = classify_flakiness(failure_rate)
    else:
        failure_rate = None
        rate_classification = "Unknown"

    failure_evidence.sort(
        key=lambda item: item["run_index"]
    )

    for count, item in enumerate(
        failure_evidence,
        start=1
    ):
        item["failure_count"] = count

    return {
        "total_runs": total_runs,
        "passed": passed,
        "failed": failed,
        "unknown":unknown,
        "failure_rate": (
            round(failure_rate, 2)
            if failure_rate is not None
            else None
        ),
        "rate_classification": rate_classification,
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


# ----------------------------------------------------------------------
# ORDER / STATE DEPENDENCE SUPPORT
#
# Runs a sequence of pytest node IDs in ONE subprocess invocation
# (e.g. `pytest test_A test_B`) so that whatever state test_A leaves
# behind is present when test_B runs. Only the outcome of the last
# test in the sequence (the target) is tracked; the earlier tests are
# just there to establish preceding state/order.
# ----------------------------------------------------------------------

def _extract_target_status(stdout: str, target_test: str) -> str:
    """
    Find the target test's own PASSED/FAILED/ERROR outcome in
    `pytest -v` output, e.g.:

        path/test_file.py::test_A PASSED
        path/test_file.py::test_B FAILED

    Returns "UNKNOWN" if the target's result line can't be confidently
    found -- e.g. an earlier test in the sequence aborted the run
    before the target ever executed. Callers must treat "UNKNOWN" as
    unknown rather than guess pass/fail.
    """

    for line in stdout.splitlines():
        match = re.match(r"^(\S+)\s+(PASSED|FAILED|ERROR)\b", line.strip())
        if match and match.group(1) == target_test:
            return "PASSED" if match.group(2) == "PASSED" else "FAILED"

    return "UNKNOWN"


def _extract_target_failure_block(stdout: str, target_test: str) -> str:
    """
    Isolate the portion of pytest's output that covers the target
    test's own failure detail.

    pytest prints a "___ test_name ___" header before each failing
    test's traceback. Without this isolation, a naive scan for "E "
    lines across the whole sequence's stdout would pick up an earlier
    test's failure instead of the target's -- which is exactly what
    we must not do when an earlier test in the sequence also fails.

    Returns an empty string if no matching block is found.
    """

    target_name = target_test.split("::")[-1]
    lines = stdout.splitlines()

    start = None
    for index, line in enumerate(lines):
        clean_line = line.strip()
        if clean_line.startswith("___") and target_name in clean_line:
            start = index
            break

    if start is None:
        return ""

    end = len(lines)
    for index in range(start + 1, len(lines)):
        clean_line = lines[index].strip()
        if clean_line.startswith("___") or clean_line.startswith("==="):
            end = index
            break

    return "\n".join(lines[start:end])


def run_single_sequence_test(
    execution_config: dict,
    run_index: int
) -> dict:
    """
    Run a sequence of pytest node IDs in one subprocess and extract
    the outcome of just the target test (the last node in the
    sequence).

    Returns:
        {
            "run_index": run_index,
            "status": "PASSED" | "FAILED" | "UNKNOWN",
            "evidence": ... or None
        }

    "UNKNOWN" means the target's own outcome could not be established
    (e.g. the sequence timed out, or an earlier test in the sequence
    prevented the target from ever running) -- it is never treated as
    a failure of the target.
    """

    sequence = execution_config["sequence"]
    target_test = sequence[-1]
    timeout = execution_config.get("timeout", 60)

    try:
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "-v"] + sequence,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        # The target's own outcome can't be established when the
        # sequence itself never finished, so status stays UNKNOWN.
        # This evidence describes the sequence timing out -- it is
        # NOT target failure evidence.
        return {
            "run_index": run_index,
            "status": "UNKNOWN",
            "evidence": {
                "run_index": run_index,
                "line": "UNKNOWN",
                "assertion": (
                    f"Sequence execution timed out after "
                    f"{timeout} seconds before the target test's "
                    f"outcome could be determined."
                ),
                "error_type": "Timeout",
                "stderr": None
            }
        }

    target_status = _extract_target_status(res.stdout, target_test)

    if target_status == "UNKNOWN":
        # Could not confidently locate the target's own result line --
        # e.g. an earlier test in the sequence aborted the run before
        # the target executed. Do not attribute any evidence from the
        # sequence to the target in this case.
        return {
            "run_index": run_index,
            "status": "UNKNOWN",
            "evidence": None
        }

    if target_status == "PASSED":
        return {
            "run_index": run_index,
            "status": "PASSED",
            "evidence": None
        }

    # target_status == "FAILED": isolate evidence to the target test's
    # own failure block, not the first failure found anywhere in the
    # sequence's output.
    stdout = res.stdout or ""
    stderr = res.stderr or ""

    failure_block = _extract_target_failure_block(stdout, target_test)

    line_num = "UNKNOWN"
    assertion_text = "No assertion isolated."
    error_type = "TestFailure"

    exception_patterns = [
        r"E\s+([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))(?::|$)",
        r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):"
    ]

    for pattern in exception_patterns:
        match = re.search(pattern, failure_block)
        if match:
            error_type = match.group(1)
            break

    for line in failure_block.splitlines():
        clean_line = line.strip()
        match = re.search(r"\.py:(\d+):", clean_line)
        if match:
            line_num = match.group(1)
            break

    evidence_lines = [
        re.sub(r"^E\s+", "", line.strip())
        for line in failure_block.splitlines()
        if line.strip().startswith("E ")
    ]

    if evidence_lines:
        assertion_text = "\n".join(evidence_lines)
    elif stderr.strip():
        # Fall back to stderr only when no target-specific assertion
        # text was isolated -- still associated with this run, not
        # blindly with "the first thing in stdout".
        assertion_text = stderr.strip()

    return {
        "run_index": run_index,
        "status": "FAILED",
        "evidence": {
            "run_index": run_index,
            "line": line_num,
            "assertion": assertion_text,
            "error_type": error_type,
            "stderr": stderr if stderr.strip() else None
        }
    }


def run_sequence_test(execution_config: dict) -> dict:
    """
    Execute a pytest sequence repeatedly, tracking only the target
    (last) test's outcome each time.

    per run, not the three-state "status" produced above. Wiring the
    two together (including how "UNKNOWN" runs should be counted) is
    intentionally left for the next change, per scope.
    """

    runs = execution_config["runs"]
    sequence = execution_config["sequence"]
    prefix = f"Order {' -> '.join(sequence)}"

    run_results = []

    for i in range(1, runs + 1):
        result = run_single_sequence_test(
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