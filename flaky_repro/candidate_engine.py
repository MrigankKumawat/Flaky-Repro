from flaky_repro.experiment_engine import run_initial_investigation
from flaky_repro.comparison_engine import compare_results
import numbers

def normalize_investigation(investigation_results:dict)->list:
    candidates = []
    
    # 1. Worker Experiment
    for exp in investigation_results.get("worker_experiment", []):
        candidates.append({
            "type":"worker",
            "condition":{
                "worker":exp['worker'],
            },
            "result":exp['result']
        })
        
    # 2. Timing Delay Experiment
    for exp in investigation_results.get("timing_experiment", []):
        candidates.append({
            "type":"timing_delay",
            "condition":{
                "timing_delay":exp['timing_delay']
            },
            "result":exp['result']
        })
    
    
    # 3. Mode Experiment
    for exp in investigation_results.get("mode_experiment", []):
        candidates.append({
            "type":"mode",
            "condition":{
                "mode":exp['mode'],
                "workers":exp['workers']
            },
            "result":exp['result']
        })
        
    return candidates


def validate_candidate(candidate: dict):

    # 1. Candidate exists
    if not candidate:
        return {
            "valid": False,
            "reason": "Missing candidate"
        }

    if not isinstance(candidate, dict):
        return {
            "valid": False,
            "reason": "Candidate must be a dictionary"
        }

    # 2. Type exists and is valid
    candidate_type = candidate.get("type")

    if candidate_type is None:
        return {
            "valid": False,
            "reason": "Missing candidate type"
        }

    if candidate_type not in ("worker", "timing_delay", "mode"):
        return {
            "valid": False,
            "reason": "Invalid candidate type"
        }

    # 3. Condition exists
    condition = candidate.get("condition")

    if not condition:
        return {
            "valid": False,
            "reason": "Missing condition"
        }

    # 4. Result exists
    result = candidate.get("result")

    if not result:
        return {
            "valid": False,
            "reason": "Missing result"
        }

    if not isinstance(result, dict):
        return {
            "valid": False,
            "reason": "Result must be a dictionary"
        }

    # 5. Total runs
    total_runs = result.get("total_runs")

    if total_runs is None:
        return {
            "valid": False,
            "reason": "Missing total runs"
        }

    if not isinstance(total_runs, int):
        return {
            "valid": False,
            "reason": "Invalid total runs"
        }

    if total_runs <= 0:
        return {
            "valid": False,
            "reason": "Total runs must be greater than zero"
        }

    # 6. Passed and failed
    passed = result.get("passed")
    failed = result.get("failed")

    if passed is None or failed is None:
        return {
            "valid": False,
            "reason": "Passed or failed value is missing"
        }

    if not isinstance(passed, int) or not isinstance(failed, int):
        return {
            "valid": False,
            "reason": "Passed and failed must be integers"
        }

    if passed < 0 or failed < 0:
        return {
            "valid": False,
            "reason": "Passed and failed cannot be negative"
        }

    if passed + failed != total_runs:
        return {
            "valid": False,
            "reason": "Passed + failed does not equal total runs"
        }

    # 7. Failure rate
    failure_rate = result.get("failure_rate")

    if failure_rate is None:
        return {
            "valid": False,
            "reason": "Failure rate is missing"
        }

    if not isinstance(failure_rate, numbers.Number):
        return {
            "valid": False,
            "reason": "Invalid failure rate"
        }

    if not 0 <= failure_rate <= 100:
        return {
            "valid": False,
            "reason": "Failure rate must be between 0 and 100"
        }

    # Candidate is structurally valid
    return {
        "valid": True,
        "reason": None
    }
    

def classify_failure_behavior(failure_rate):
    if failure_rate is None:
        return "Failure rate don't exist"
    
    if failure_rate == 0:
        return "Consistently Passing"
    
    if failure_rate >=1 and failure_rate <= 99:
        return "Intermittent"
    
    if failure_rate == 100:
        return "Consistently Failing"
    
    
def calculate_candidate_effect(baseline_result, candidate):
    result = compare_results(
        baseline_result,
        candidate['result']
    )
    
    return result

def classify_candidate(baseline_result, candidate):
    baseline_behavior = classify_failure_behavior(
        baseline_result["failure_rate"]
    )
    candidate_behavior = classify_failure_behavior(
        candidate["result"]["failure_rate"]
    )

    baseline_failure_rate = baseline_result["failure_rate"]
    candidate_failure_rate = candidate["result"]["failure_rate"]

    if baseline_behavior == "Consistently Passing":
        if candidate_behavior in ("Intermittent", "Consistently Failing"):
            return {"classification": "STRONG"}

        return {"classification": "NO_SIGNAL"}

    if baseline_behavior == "Intermittent":
        rate_increase = candidate_failure_rate - baseline_failure_rate

        if rate_increase <= 0:
            return {"classification": "NO_SIGNAL"}

        if rate_increase < 10:
            return {"classification": "WEAK"}

        return {"classification": "STRONG"}

    if baseline_behavior == "Consistently Failing":
        if candidate_behavior == "Consistently Failing":
            return {"classification": "NO_SIGNAL"}

        if candidate_behavior in ("Intermittent", "Consistently Passing"):
            return {"classification": "WEAK"}

    return {"classification": "NO_SIGNAL"}
    
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("       CANDIDATE CLASSIFICATION TEST")
    print("=" * 60)

    def make_result(failure_rate):
        total_runs = 100
        failed = int(failure_rate)
        passed = total_runs - failed

        return {
            "total_runs": total_runs,
            "passed": passed,
            "failed": failed,
            "failure_rate": failure_rate
        }

    test_cases = [
        # Baseline Passing
        ("Passing → Passing", 0, 0, "NO_SIGNAL"),
        ("Passing → Intermittent", 0, 50, "STRONG"),
        ("Passing → Failing", 0, 100, "STRONG"),

        # Baseline Intermittent
        ("Intermittent → Same", 30, 30, "NO_SIGNAL"),
        ("Intermittent → Weak Increase", 30, 35, "WEAK"),
        ("Intermittent → Strong Increase", 30, 60, "STRONG"),
        ("Intermittent → Lower", 30, 10, "NO_SIGNAL"),

        # Baseline Failing
        ("Failing → Failing", 100, 100, "NO_SIGNAL"),
        ("Failing → Intermittent", 100, 50, "WEAK"),
        ("Failing → Passing", 100, 0, "WEAK"),
    ]

    passed_tests = 0
    failed_tests = 0

    for name, baseline_rate, candidate_rate, expected in test_cases:

        baseline = make_result(baseline_rate)

        candidate = {
            "type": "worker",
            "condition": {
                "worker": 4
            },
            "result": make_result(candidate_rate)
        }

        actual_result = classify_candidate(
            baseline,
            candidate
        )

        actual = actual_result["classification"]

        status = "PASS" if actual == expected else "FAIL"
        if status == "PASS":
            passed_tests += 1
        else:
            failed_tests += 1

        print(
            f"\n{status} | {name}"
            f"\n   Baseline   : {baseline_rate}%"
            f"\n   Candidate  : {candidate_rate}%"
            f"\n   Expected   : {expected}"
            f"\n   Actual     : {actual}"
        )

    print("\n" + "=" * 60)
    print("             TEST SUMMARY")
    print("=" * 60)

    print(f"Total tests : {len(test_cases)}")
    print(f"Passed      : {passed_tests}")
    print(f"Failed      : {failed_tests}")

    if failed_tests == 0:
        print("\nALL CLASSIFICATION TESTS PASSED")
    else:
        print("\nSOME CLASSIFICATION TESTS FAILED")

    print("=" * 60)