from flaky_repro.experiment_engine import worker_experiment
from flaky_repro.experiment_engine import timing_experiment
from flaky_repro.experiment_engine import mode_experiment

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
    


def main():

    target_test = "examples/test_timing_flaky.py::test_timing_behavior"

    runs = 5
    reproduction_runs = 3

    # Reproduction environment
    mode = "Parallel"
    workers_count = 4

    candidates = [

        {
            "type": "worker",
            "condition": {
                "worker": 4
            }
        },

        {
            "type": "timing_delay",
            "condition": {
                "timing_delay": 20
            }
        },

        {
            "type": "mode",
            "condition": {
                "mode": "Parallel",
                "workers": 8
            }
        }
    ]

    print("\n" + "=" * 60)
    print("       REPRODUCTION ENGINE TEST")
    print("=" * 60)

    print("\n--- CONFIGURATION ---")
    print(f"Target test       : {target_test}")
    print(f"Runs per attempt  : {runs}")
    print(f"Reproduction runs : {reproduction_runs}")
    print(f"Mode              : {mode}")
    print(f"Workers           : {workers_count}")

    passed = 0

    for index, candidate in enumerate(candidates, start=1):

        print("\n" + "=" * 60)
        print(f"             CANDIDATE {index}")
        print("=" * 60)

        print(f"Type      : {candidate['type']}")
        print(f"Condition : {candidate['condition']}")

        print("\nRunning reproduction...")

        result = run_reproduction(
            candidate=candidate,
            target_test=target_test,
            runs=runs,
            reproduction_runs=reproduction_runs,
            mode=mode,
            workers_count=workers_count
        )

        reproduction_results = result["reproduction_runs"]

        actual_runs = len(reproduction_results)

        print("\nResults:")

        for repetition in reproduction_results:

            run_index = repetition["run_index"]
            experiment_result = repetition["result"]

            print(f"\nRun {run_index}")

            # Worker / Timing experiments return a list
            if candidate["type"] in ("worker", "timing_delay"):

                experiment = experiment_result[0]

                print(
                    f"Failure Rate : "
                    f"{experiment['result']['failure_rate']}%"
                )

            # Mode experiment returns two results
            elif candidate["type"] == "mode":

                for experiment in experiment_result:

                    print(
                        f"Mode         : {experiment['mode']}"
                    )

                    print(
                        f"Workers      : {experiment['workers']}"
                    )

                    print(
                        f"Failure Rate : "
                        f"{experiment['result']['failure_rate']}%"
                    )

        print("\n" + "-" * 60)

        print(
            f"Expected repetitions : {reproduction_runs}"
        )

        print(
            f"Actual repetitions   : {actual_runs}"
        )

        # Validate structure
        valid_structure = True

        if actual_runs != reproduction_runs:
            valid_structure = False

        for repetition in reproduction_results:

            if "run_index" not in repetition:
                valid_structure = False

            if "result" not in repetition:
                valid_structure = False

        if valid_structure:

            print("✅ PASS")
            passed += 1

        else:

            print("❌ FAIL")

    print("\n" + "=" * 60)
    print("             TEST SUMMARY")
    print("=" * 60)

    print(f"Candidates tested : {len(candidates)}")
    print(f"Candidates passed : {passed}")
    print(f"Candidates failed : {len(candidates) - passed}")

    if passed == len(candidates):

        print("\n✅ ALL REPRODUCTION TESTS PASSED")

    else:

        print("\n❌ SOME REPRODUCTION TESTS FAILED")

    print("=" * 60)


if __name__ == "__main__":
    main()