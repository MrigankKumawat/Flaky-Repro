from flaky_repro.runner import run_parallel_test
from flaky_repro.runner import run_sequential_test

def worker_experiment(target_test:str, runs:int, workers_count:list):
    all_worker_results = []
    
    for worker in workers_count:
        result = run_parallel_test(target_test, runs, worker)
        
        all_worker_results.append({
            "worker":worker,
            "result":result
        })
        
    return all_worker_results
        
def timing_experiment(
    target_test: str,
    runs: int,
    mode: str,
    workers_count: int,
    timing_values: list
):
    all_timing_results = []

    for time_value in timing_values:
        delay = time_value / 1000

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
                f"Invalid execution mode: {mode}"
            )

        all_timing_results.append({
            "timing_delay": time_value,
            "result": result
        })

    return all_timing_results
        
def mode_experiment(
    target_test: str,
    runs: int,
    workers_count: int,
    sequential_result=None,
    parallel_result=None
):
    results = []

    if sequential_result is None or sequential_result.get("total_runs") != runs:
        sequential_result = run_sequential_test(
            target_test,
            runs,
            timing_delay=0
        )

    results.append({
        "mode": "Sequential",
        "workers": 1,
        "result": sequential_result
    })

    if parallel_result is None or parallel_result.get("total_runs") != runs:
        parallel_result = run_parallel_test(
            target_test,
            runs,
            workers_count,
            timing_delay=0
        )

    results.append({
        "mode": "Parallel",
        "workers": workers_count,
        "result": parallel_result
    })

    return results
        
def run_initial_investigation(
    target_test: str,
    runs: int,
    mode: str,
    workers_count: list,
    timing_delay: list,
    sequential_result=None
):

    # 1. Worker Experiment
    worker_experiment_investigation = worker_experiment(
        target_test=target_test,
        runs=runs,
        workers_count=workers_count
    )

    # 2. Timing Experiment
    timing_delay_investigation = timing_experiment(
        target_test=target_test,
        runs=runs,
        mode=mode,
        workers_count=workers_count[0],
        timing_values=timing_delay
    )

    # 3. Mode Experiment
    parallel_4_result = None

    for experiment in worker_experiment_investigation:
        if experiment["worker"] == 4:
            parallel_4_result = experiment["result"]
            break

    mode_investigation = mode_experiment(
        target_test=target_test,
        runs=runs,
        workers_count=4,
        sequential_result=sequential_result,
        parallel_result=parallel_4_result
    )
    return {
        "worker_experiment": worker_experiment_investigation,
        "timing_experiment": timing_delay_investigation,
        "mode_experiment": mode_investigation
    }
    
if __name__ == "__main__":

    target_test = "examples/test_timing_flaky.py::test_timing_behavior"
    runs = 5

    workers_count = [2, 4, 8]
    timing_delay = [10, 20, 50]
    mode = "Parallel"
    
    result = run_initial_investigation(
        target_test=target_test,
        runs=runs,
        mode=mode,
        workers_count=workers_count,
        timing_delay=timing_delay
    )

    print("\n" + "=" * 60)
    print("        INITIAL INVESTIGATION TEST")
    print("=" * 60)

    print("\n--- WORKER EXPERIMENTS ---")
    for experiment in result["worker_experiment"]:
        print(
            f"Workers: {experiment['worker']} | "
            f"Failure Rate: {experiment['result']['failure_rate']}%"
        )

    print("\n--- TIMING EXPERIMENTS ---")
    for experiment in result["timing_experiment"]:
        print(
            f"Delay: {experiment['timing_delay']} ms | "
            f"Failure Rate: {experiment['result']['failure_rate']}%"
        )

    print("\n--- MODE EXPERIMENTS ---")
    for experiment in result["mode_experiment"]:
        print(
            f"Mode: {experiment['mode']} | "
            f"Workers: {experiment['workers']} | "
            f"Failure Rate: {experiment['result']['failure_rate']}%"
        )

    print("\n" + "=" * 60)
    print("        INITIAL INVESTIGATION COMPLETE")
    print("=" * 60)