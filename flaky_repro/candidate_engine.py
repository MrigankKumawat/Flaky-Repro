from flaky_repro.experiment_engine import run_initial_investigation
from flaky_repro.comparison_engine import compare_results
from flaky_repro.runner import run_sequential_test
from flaky_repro.runner import run_parallel_test
# from flaky_repro.experiment_engine import worker_experiment
# from flaky_repro.experiment_engine import timing_experiment
# from flaky_repro.experiment_engine import mode_experiment
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

def prepare_candidates(baseline_result, candidates):
    prepared_candidates = []

    for candidate in candidates:

        # 1. Classify candidate
        classification_result = classify_candidate(
            baseline_result,
            candidate
        )

        # 2. Calculate effect
        effect = calculate_candidate_effect(
            baseline_result,
            candidate
        )

        # 3. Preserve original candidate
        prepared_candidate = candidate.copy()

        # 4. Attach classification
        prepared_candidate["classification"] = (
            classification_result["classification"]
        )

        # 5. Attach effect
        prepared_candidate["effect"] = effect

        prepared_candidates.append(prepared_candidate)

    return prepared_candidates

def rank_candidates(candidates):
    ranked_candidates = []

    for candidate in candidates:

        classification = candidate.get("classification")

        # Ignore candidates with no useful signal
        if classification == "NO_SIGNAL":
            continue

        # Classification priority
        if classification == "STRONG":
            base_score = 100

        elif classification == "WEAK":
            base_score = 50

        else:
            continue

        # Get failure-rate effect
        effect = candidate.get("effect")

        if not effect:
            continue

        failure_rate_delta = effect.get(
            "comparison",
            {}
        ).get(
            "failure_rate_delta",
            0
        )

        # Magnitude of the observed effect
        effect_magnitude = abs(
            failure_rate_delta
        )

        # Final score
        score = base_score + effect_magnitude

        # Preserve candidate and attach ranking information
        ranked_candidate = candidate.copy()

        ranked_candidate["effect_magnitude"] = (
            effect_magnitude
        )

        ranked_candidate["score"] = score

        ranked_candidates.append(
            ranked_candidate
        )

    # Highest score first
    ranked_candidates.sort(
        key=lambda candidate: candidate["score"],
        reverse=True
    )

    # Assign rank
    for index, candidate in enumerate(
        ranked_candidates,
        start=1
    ):
        candidate["rank"] = index

    return ranked_candidates

def build_rankable_candidates(baseline_result, candidates):
    """
    Complete classification + effect preparation
    before ranking.
    """

    prepared_candidates = []

    for candidate in candidates:

        classified_result = classify_candidate(
            baseline_result,
            candidate
        )

        prepared_candidate = candidate.copy()

        prepared_candidate["classification"] = (
            classified_result["classification"]
        )

        effect = calculate_candidate_effect(
            baseline_result,
            candidate
        )

        prepared_candidate["effect"] = effect

        prepared_candidates.append(prepared_candidate)

    return prepared_candidates

def select_top_candidates(ranked_candidates, count = 3):
    rank_cand = ranked_candidates[:count]

    return rank_cand

def run_candidate_repetitions(
    candidate,
    target_test,
    runs,
    repeated_runs,
    mode,
    workers_count
):
    candidate_type = candidate["type"]
    candidate_condition = candidate["condition"]

    repetitions = []

    for repeats in range(1, repeated_runs + 1):

        if candidate_type == "worker":

            result = run_parallel_test(
                target_test,
                runs,
                candidate_condition["worker"]
            )

        elif candidate_type == "timing_delay":

            delay = candidate_condition["timing_delay"] / 1000

            if mode == "Sequential":
                result = run_sequential_test(
                    target_test,
                    runs,
                    delay
                )

            elif mode == "Parallel":
                result = run_parallel_test(
                    target_test,
                    runs,
                    workers_count,
                    delay
                )

            else:
                raise ValueError(
                    f"Invalid mode: {mode}"
                )

        elif candidate_type == "mode":

            candidate_mode = candidate_condition["mode"]
            candidate_workers = candidate_condition["workers"]

            if candidate_mode == "Sequential":

                result = run_sequential_test(
                    target_test,
                    runs,
                    timing_delay=0
                )

            elif candidate_mode == "Parallel":

                result = run_parallel_test(
                    target_test,
                    runs,
                    candidate_workers,
                    timing_delay=0
                )

            else:
                raise ValueError(
                    f"Invalid mode: {candidate_mode}"
                )

        else:
            raise ValueError(
                f"Invalid candidate type: {candidate_type}"
            )

        repetitions.append({
            "run_index": repeats,
            "result": result
        })

    return {
        "candidate": {
            "type": candidate_type,
            "condition": candidate_condition
        },
        "repetitions": repetitions
    }

def analyze_repeated_candidate(
    baseline_result,
    repeated_result
):
    repetitions = repeated_result["repetitions"]

    if not repetitions:
        return {
            "candidate": repeated_result["candidate"],
            "repetitions": [],
            "analysis": None
        }

    failure_rates = []
    effects = []

    for repeat in repetitions:

        result = repeat["result"]

        # Failure rate
        failure_rate = result["failure_rate"]

        failure_rates.append(failure_rate)

        # Compare against baseline
        compare_effect = compare_results(
            baseline_result,
            result
        )

        effects.append(compare_effect)


    total_repetitions = len(failure_rates)

    average_failure_rate = (
        sum(failure_rates) / total_repetitions
    )

    min_failure_rate = min(failure_rates)

    max_failure_rate = max(failure_rates)

    failure_rate_range = (
        max_failure_rate - min_failure_rate
    )


    return {
        "candidate": repeated_result["candidate"],

        "repetitions": repetitions,

        "analysis": {
            "total_repetitions": total_repetitions,

            "failure_rate": {
                "average": round(average_failure_rate, 2),
                "minimum": min_failure_rate,
                "maximum": max_failure_rate,
                "range": failure_rate_range
            },

            "effects": effects
        }
    }

def main():

    print("\n" + "=" * 60)
    print("       REPEATED CANDIDATE ANALYSIS TEST")
    print("=" * 60)

    # --------------------------------------------------
    # BASELINE
    # --------------------------------------------------

    baseline_result = {
        "total_runs": 5,
        "passed": 4,
        "failed": 1,
        "failure_rate": 20.0
    }

    # --------------------------------------------------
    # SIMULATED REPEATED RESULT
    # --------------------------------------------------

    repeated_result = {
        "candidate": {
            "type": "mode",
            "condition": {
                "mode": "Parallel",
                "workers": 8
            }
        },

        "repetitions": [

            {
                "run_index": 1,
                "result": {
                    "total_runs": 5,
                    "passed": 1,
                    "failed": 4,
                    "failure_rate": 80.0
                }
            },

            {
                "run_index": 2,
                "result": {
                    "total_runs": 5,
                    "passed": 0,
                    "failed": 5,
                    "failure_rate": 100.0
                }
            },

            {
                "run_index": 3,
                "result": {
                    "total_runs": 5,
                    "passed": 1,
                    "failed": 4,
                    "failure_rate": 80.0
                }
            }
        ]
    }

    print("\n--- BASELINE ---")

    print(
        f"Failure Rate : "
        f"{baseline_result['failure_rate']}%"
    )

    print("\n--- CANDIDATE ---")

    print(
        f"Type      : "
        f"{repeated_result['candidate']['type']}"
    )

    print(
        f"Condition : "
        f"{repeated_result['candidate']['condition']}"
    )

    # --------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------

    print("\n" + "-" * 60)
    print("RUNNING ANALYSIS")
    print("-" * 60)

    analysis_result = analyze_repeated_candidate(
        baseline_result=baseline_result,
        repeated_result=repeated_result
    )

    # --------------------------------------------------
    # DISPLAY FAILURE RATE ANALYSIS
    # --------------------------------------------------

    print("\n--- FAILURE RATE ANALYSIS ---")

    analysis = analysis_result["analysis"]

    print(
        f"Total repetitions : "
        f"{analysis['total_repetitions']}"
    )

    print(
        f"Average failure rate : "
        f"{analysis['failure_rate']['average']}%"
    )

    print(
        f"Minimum failure rate : "
        f"{analysis['failure_rate']['minimum']}%"
    )

    print(
        f"Maximum failure rate : "
        f"{analysis['failure_rate']['maximum']}%"
    )

    print(
        f"Failure rate range : "
        f"{analysis['failure_rate']['range']} pp"
    )

    # --------------------------------------------------
    # DISPLAY INDIVIDUAL EFFECTS
    # --------------------------------------------------

    print("\n--- REPETITION EFFECTS ---")

    for index, effect in enumerate(
        analysis["effects"],
        start=1
    ):

        print(
            f"\nRepetition {index}"
        )

        print(
            f"Effect : {effect}"
        )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("             TEST VALIDATION")
    print("=" * 60)

    expected_failure_rates = [
        80.0,
        100.0,
        80.0
    ]

    expected_average = 86.66666666666667
    expected_minimum = 80.0
    expected_maximum = 100.0
    expected_range = 20.0

    actual_rates = [
        repetition["result"]["failure_rate"]
        for repetition
        in analysis_result["repetitions"]
    ]

    print(
        f"Expected failure rates : "
        f"{expected_failure_rates}"
    )

    print(
        f"Actual failure rates   : "
        f"{actual_rates}"
    )

    print(
        f"\nExpected average : "
        f"{expected_average}"
    )

    print(
        f"Actual average   : "
        f"{analysis['failure_rate']['average']}"
    )

    print(
        f"\nExpected minimum : "
        f"{expected_minimum}"
    )

    print(
        f"Actual minimum   : "
        f"{analysis['failure_rate']['minimum']}"
    )

    print(
        f"\nExpected maximum : "
        f"{expected_maximum}"
    )

    print(
        f"Actual maximum   : "
        f"{analysis['failure_rate']['maximum']}"
    )

    print(
        f"\nExpected range : "
        f"{expected_range}"
    )

    print(
        f"Actual range   : "
        f"{analysis['failure_rate']['range']}"
    )

    # --------------------------------------------------
    # FINAL CHECK
    # --------------------------------------------------

    rates_correct = (
        actual_rates == expected_failure_rates
    )

    average_correct = abs(
        analysis["failure_rate"]["average"]
        - expected_average
    ) < 0.001

    minimum_correct = (
        analysis["failure_rate"]["minimum"]
        == expected_minimum
    )

    maximum_correct = (
        analysis["failure_rate"]["maximum"]
        == expected_maximum
    )

    range_correct = (
        analysis["failure_rate"]["range"]
        == expected_range
    )

    effects_correct = (
        len(analysis["effects"]) == 3
    )

    if (
        rates_correct
        and average_correct
        and minimum_correct
        and maximum_correct
        and range_correct
        and effects_correct
    ):
        print(
            "\n✅ REPEATED ANALYSIS TEST PASSED"
        )

    else:
        print(
            "\n❌ REPEATED ANALYSIS TEST FAILED"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()