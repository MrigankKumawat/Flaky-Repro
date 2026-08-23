from flaky_repro.experiment_engine import worker_experiment
from flaky_repro.experiment_engine import timing_experiment
from flaky_repro.experiment_engine import mode_experiment
from flaky_repro.comparison_engine import compare_results
from flaky_repro.candidate_engine import calculate_consistency

def run_reproduction(
    candidate,
    target_test,
    runs,
    reproduction_runs,
    mode,
    workers_count
):
    reproduction_results = []

    for repeat in range(1, reproduction_runs+1):

        candidate_type = candidate['type']
        candidate_condition = candidate["condition"]

        if candidate_type == "worker":
            work_exp = worker_experiment(
                target_test=target_test,
                runs=runs,
                workers_count=[candidate_condition['worker']]
            )
            reproduction_results.append({
                "run_index":repeat,
                "result":work_exp
            })

        if candidate_type == "timing_delay":
            time_exp = timing_experiment(
                target_test=target_test,
                runs=runs,
                mode=mode,
                workers_count=workers_count,
                timing_values=[candidate_condition["timing_delay"]]
            )

            reproduction_results.append({
                "run_index": repeat,
                "result": time_exp
            })

        if candidate_type == "mode":
            mode_exp = mode_experiment(
                target_test=target_test,
                runs=runs,
                workers_count=candidate_condition["workers"]
            )

            reproduction_results.append({
                "run_index": repeat,
                "result": mode_exp
            })

    return{
        "candidate": {
            "type": candidate_type,
            "condition": candidate_condition
        },
        "reproduction_runs": reproduction_results
    }


def analyze_reproduction(
    baseline_result,
    reproduction_result
):

    candidate = reproduction_result["candidate"]
    repetitions = reproduction_result["reproduction_runs"]

    failure_rates = []
    effects = []

    for repeat in repetitions:

        run_index = repeat["run_index"]
        experiment_result = repeat["result"]

        actual_result = None

        if candidate["type"] == "worker":

            actual_result = experiment_result[0]["result"]

        elif candidate["type"] == "timing_delay":

            actual_result = experiment_result[0]["result"]

        elif candidate["type"] == "mode":

            candidate_mode = candidate["condition"]["mode"]
            candidate_workers = candidate["condition"]["workers"]

            for mode_result in experiment_result:

                if (
                    mode_result["mode"] == candidate_mode
                    and mode_result["workers"] == candidate_workers
                ):
                    actual_result = mode_result["result"]
                    break

        if actual_result is None:
            continue

        failure_rate = actual_result["failure_rate"]

        failure_rates.append(failure_rate)

        compare_effect = compare_results(
            baseline_result,
            actual_result
        )

        effects.append({
            "repetition": run_index,
            "effect": compare_effect
        })

    if not failure_rates:

        return {
            "candidate": candidate,
            "reproduction": None
        }

    total_repetitions = len(failure_rates)

    average_rate = sum(failure_rates) / total_repetitions
    min_rate = min(failure_rates)
    max_rate = max(failure_rates)
    range_rate = max_rate - min_rate

    consistency = calculate_consistency(
        [item["effect"] for item in effects]
    )

    return {
        "candidate": candidate,

        "reproduction": {

            "total_repetitions": total_repetitions,

            "failure_rate": {
                "average": round(average_rate, 2),
                "minimum": min_rate,
                "maximum": max_rate,
                "range": range_rate
            },

            "effects": effects,

            "consistency": consistency
        }
    }
    
def classify_reproduction(
    reproduction_analysis
):
    failure_rate_deltas = []
    
    candidate = reproduction_analysis["candidate"]
    reproduction = reproduction_analysis["reproduction"]
    consistency_rate = reproduction["consistency"]["consistency_rate"]
    effects = reproduction["effects"]
    
    for effect in effects:
        delta = effect["effect"]["comparison"]["failure_rate_delta"]

        failure_rate_deltas.append(delta)        
        
        average_effect = (
            sum(failure_rate_deltas) / len(failure_rate_deltas)
            if failure_rate_deltas
            else 0.0
        )
        
        if consistency_rate >= 80 and average_effect > 0:
            classification = "REPRODUCED"

        elif consistency_rate >= 50 and average_effect > 0:
            classification = "PARTIAL"

        else:
            classification = "NOT_REPRODUCED"
        
        return {
            "candidate": candidate,
            "classification": classification,
            "consistency_rate": consistency_rate,
            "average_effect": round(average_effect, 2),
            "total_repetitions": len(failure_rate_deltas)
        }
        
def main():

    print("\n" + "=" * 60)
    print("       REPRODUCTION CLASSIFICATION TEST")
    print("=" * 60)

    test_cases = [

        {
            "name": "Strong reproduction",
            "consistency_rate": 100.0,
            "effects": [60.0, 80.0, 70.0],
            "expected": "REPRODUCED"
        },

        {
            "name": "Partial reproduction",
            "consistency_rate": 66.67,
            "effects": [30.0, 0.0, 15.0],
            "expected": "PARTIAL"
        },

        {
            "name": "Not reproduced - low consistency",
            "consistency_rate": 33.33,
            "effects": [20.0, 0.0, 0.0],
            "expected": "NOT_REPRODUCED"
        },

        {
            "name": "Not reproduced - no effect",
            "consistency_rate": 100.0,
            "effects": [0.0, 0.0, 0.0],
            "expected": "NOT_REPRODUCED"
        }
    ]

    passed = 0

    for index, test in enumerate(test_cases, start=1):

        print("\n" + "-" * 60)
        print(f"TEST {index} | {test['name']}")
        print("-" * 60)

        effects = []

        for run_index, delta in enumerate(
            test["effects"],
            start=1
        ):

            effects.append({
                "repetition": run_index,
                "effect": {
                    "comparison": {
                        "failure_rate_delta": delta
                    }
                }
            })

        reproduction_analysis = {

            "candidate": {
                "type": "worker",
                "condition": {
                    "worker": 4
                }
            },

            "reproduction": {

                "total_repetitions": len(effects),

                "failure_rate": {
                    "average": 80.0,
                    "minimum": 60.0,
                    "maximum": 100.0,
                    "range": 40.0
                },

                "effects": effects,

                "consistency": {
                    "total_repetitions": len(effects),
                    "increased_count": round(
                        test["consistency_rate"]
                        * len(effects)
                        / 100
                    ),
                    "consistency_rate":
                        test["consistency_rate"]
                }
            }
        }

        result = classify_reproduction(
            reproduction_analysis
        )

        actual = result["classification"]

        print(
            f"Consistency : "
            f"{result['consistency_rate']}%"
        )

        print(
            f"Average Effect : "
            f"{result['average_effect']} pp"
        )

        print(
            f"Expected : {test['expected']}"
        )

        print(
            f"Actual   : {actual}"
        )

        if actual == test["expected"]:

            print("✅ PASS")
            passed += 1

        else:

            print("❌ FAIL")

    print("\n" + "=" * 60)
    print("             TEST SUMMARY")
    print("=" * 60)

    print(f"Total tests : {len(test_cases)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {len(test_cases) - passed}")

    if passed == len(test_cases):

        print("\n✅ ALL REPRODUCTION CLASSIFICATION TESTS PASSED")

    else:

        print("\n❌ SOME REPRODUCTION CLASSIFICATION TESTS FAILED")

    print("=" * 60)


if __name__ == "__main__":
    main()