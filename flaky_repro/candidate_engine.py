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

    consistency_analysis = calculate_consistency(effects=effects)


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

            "effects": effects,
            "consistency":consistency_analysis
        }
    }

def calculate_consistency(effects:list):
    if effects is None:
        return{
            "total_repetitions": 0,
            "increased_count": 0,
            "rate_label":None,
            "consistency_rate": 0.0
        }
    increased_count = 0
    for effect in effects:
        effect_failure_rate = effect['comparison']['failure_rate_delta']

        if effect_failure_rate > 0:
            rate_label = "Increased"
            increased_count+=1
        elif effect_failure_rate <= 0:
            rate_label = "Not increased"

    total_repetitions = len(effects)
    consistency_rate = (increased_count/total_repetitions) * 100 if total_repetitions !=0.0 else 0.0

    return{
        "total_repetitions":total_repetitions,
        "increased_count":increased_count,
        "rate_label":rate_label,
        "consistency_rate":consistency_rate
    }

def confirm_candidate(repeated_analysis):
    failure_rate_deltas = []

    consistency_rate = repeated_analysis['analysis']['consistency']['consistency_rate']
    effects = repeated_analysis["analysis"]["effects"]

    for effect in effects:
        delta = effect["comparison"]["failure_rate_delta"]
        failure_rate_deltas.append(delta)

    average_effect = sum(failure_rate_deltas) / len(failure_rate_deltas)

    if consistency_rate >= 80 and average_effect > 0:
        classification = "Confirmed"
    elif consistency_rate >= 50 and average_effect > 0:
        classification = "Weak"
    else:
        classification = "Rejected"

    return{
        "classification":classification,
        "consistency_rate":consistency_rate,
        "average_effect":round(average_effect, 2),
    }


def main():

    print("\n" + "=" * 60)
    print("          CANDIDATE CONFIRMATION TEST")
    print("=" * 60)

    def make_analysis(consistency_rate, deltas):

        effects = []

        for delta in deltas:
            effects.append({
                "comparison": {
                    "failure_rate_delta": delta
                }
            })

        return {
            "analysis": {
                "consistency": {
                    "consistency_rate": consistency_rate
                },
                "effects": effects
            }
        }

    test_cases = [

        # CONFIRMED
        {
            "name": "Strong candidate",
            "input": make_analysis(100.0, [60.0, 80.0, 60.0]),
            "expected": "Confirmed"
        },

        # WEAK
        {
            "name": "Weak candidate",
            "input": make_analysis(66.67, [20.0, -5.0, 30.0]),
            "expected": "Weak"
        },

        # REJECTED
        {
            "name": "Rejected candidate",
            "input": make_analysis(33.33, [20.0, -10.0, -5.0]),
            "expected": "Rejected"
        },

        # ZERO EFFECT
        {
            "name": "No effect",
            "input": make_analysis(100.0, [0.0, 0.0, 0.0]),
            "expected": "Rejected"
        }
    ]

    passed = 0

    print()

    for test in test_cases:

        result = confirm_candidate(test["input"])

        actual = result["classification"]

        if actual == test["expected"]:
            print(f"PASS | {test['name']}")
            passed += 1
        else:
            print(f"FAIL | {test['name']}")

        print(
            f"   Consistency : "
            f"{result['consistency_rate']}%"
        )

        print(
            f"   Avg Effect  : "
            f"{result['average_effect']} pp"
        )

        print(
            f"   Expected    : "
            f"{test['expected']}"
        )

        print(
            f"   Actual      : "
            f"{actual}"
        )

        print()

    print("=" * 60)
    print("             TEST SUMMARY")
    print("=" * 60)

    print(f"Total tests : {len(test_cases)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {len(test_cases) - passed}")

    if passed == len(test_cases):
        print("\n✅ ALL CANDIDATE CONFIRMATION TESTS PASSED")
    else:
        print("\n❌ SOME TESTS FAILED")

    print("=" * 60)


if __name__ == "__main__":
    main()