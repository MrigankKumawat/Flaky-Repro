from flaky_repro.runner import run_parallel_test
from flaky_repro.runner import run_sequential_test
from flaky_repro.runner import run_test

def worker_experiment(
    target_test:str, 
    runs:int,
    timing_delay:int,
    timeout:int,
    mode:str,
    workers_count:list
):
    config = {
        "target_test": target_test,
        "runs": runs,
        "timing_delay": timing_delay,
        "timeout": timeout,
        "mode": mode,
        "workers": workers_count
    }


    all_worker_results = []

    for worker in workers_count:

        result = run_parallel_test(target_test, runs, worker)
        
        config['workers'] = worker
        result = run_test(config)


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
    timing_delay: list,
    timeout:int
):
    config = {
        "target_test": target_test,
        "runs": runs,
        "timing_delay": timing_delay,
        "timeout": timeout,
        "mode": mode,
        "workers": workers_count
    }
    all_timing_results = []

    for time_delay in timing_delay:
        delay = time_delay / 1000

        if mode == "Sequential":
            config['timing_delay'] = delay
            result = run_test(config)

        elif mode == "Parallel":
            config['timing_delay'] = delay
            result = run_test(config)

        else:
            raise ValueError(
                f"Invalid execution mode: {mode}"
            )

        all_timing_results.append({
            "timing_delay": time_delay,
            "result": result
        })

    return all_timing_results

def mode_experiment(
    target_test: str,
    runs: int,
    timing_delay: list,
    timeout:int,
    mode:str,
    workers_count: int,
    sequential_result=None,
    parallel_result=None
):
    sequential_config = {
        "target_test": target_test,
        "runs": runs,
        "timing_delay": timing_delay,
        "timeout": timeout,
        "mode": "Sequential",
        "workers": None
    }
    parallel_config = {
        "target_test": target_test,
        "runs": runs,
        "timing_delay": timing_delay,
        "timeout": timeout,
        "mode": "Parallel",
        "workers": workers_count
    }
    results = []

    if sequential_result is None or sequential_result.get("total_runs") != runs:
        sequential_result = run_test(sequential_config)

    results.append({
        "mode": "Sequential",
        "workers": 1,
        "result": sequential_result
    })

    if parallel_result is None or parallel_result.get("total_runs") != runs:
        parallel_result = run_test(parallel_config)

    results.append({
        "mode": "Parallel",
        "workers": workers_count,
        "result": parallel_result
    })

    return results

# Timeout Experiment
def timeout_experiment(
    target_test: str,
    runs: int,
    timing_delay: int,
    timeout_values:list,
    mode: str,
    workers_count: int,
):
    config = {
        "target_test": target_test,
        "runs": runs,
        "timing_delay": timing_delay,
        "timeout": timeout_values,
        "mode": mode,
        "workers": workers_count
    }
    results = []

    for timeout in timeout_values:
        if mode == "Sequential":
            config['timeout'] = timeout
            sequential_result = run_test(config)

            results.append({
                "timeout": timeout,
                "result": sequential_result
            })

        elif mode == "Parallel":
            config['timeout'] = timeout
            parallel_result = run_test(config)

            results.append({
                "timeout": timeout,
                "result": parallel_result
            })

        else:
            raise ValueError(
                f"Invalid execution mode: {mode}"
            )

    return results

EXPERIMENT_REGISTRY = {
    "worker": worker_experiment,
    "timing": timing_experiment,
    "mode": mode_experiment,
    "timeout": timeout_experiment
}


def run_experiment(
    experiment_name: str,
    target_test: str,
    runs: int,
    **experiment_config
):
    """Execute one registered experiment."""
    if experiment_name not in EXPERIMENT_REGISTRY:
        raise ValueError(
            f"Unknown experiment: {experiment_name}. "
            f"Available experiments: {list(EXPERIMENT_REGISTRY.keys())}"
        )

    experiment = EXPERIMENT_REGISTRY[experiment_name]

    return experiment(
        target_test=target_test,
        runs=runs,
        **experiment_config
    )


def run_selected_experiments(
    target_test: str,
    runs: int,
    selected_experiments: list,
    experiment_configs: dict
):
    """
    Execute selected experiments.

    `selected_experiments` controls what runs.
    `experiment_configs` contains each experiment's parameters.
    """
    results = {}

    for experiment_name in selected_experiments:
        config = experiment_configs.get(experiment_name, {})

        results[experiment_name] = run_experiment(
            experiment_name=experiment_name,
            target_test=target_test,
            runs=runs,
            **config
        )

    return results


def run_initial_investigation(
    target_test: str,
    runs: int,
    timing_delay: list,
    timeout: list,
    mode: str,
    workers_count: list,
    sequential_result=None
):
    """
    Run the initial investigation using the experiment orchestration layer.
    """

    # ---------------------------------------------------------
    # 1. Worker Experiment
    # ---------------------------------------------------------
    worker_results = run_experiment(
        experiment_name="worker",
        target_test=target_test,
        runs=runs,
        timing_delay=0,
        timeout=timeout[0],
        mode=mode,
        workers_count=workers_count,
    )

    # Reuse the 4-worker result for the mode experiment
    parallel_4_result = None

    for experiment in worker_results:
        if experiment["worker"] == 4:
            parallel_4_result = experiment["result"]
            break

    # ---------------------------------------------------------
    # 2. Selected Experiments
    # ---------------------------------------------------------
    selected_experiments = [
        "timing",
        "mode",
        "timeout",
    ]

    experiment_configs = {
        "timing": {
            "mode": mode,
            "workers_count": workers_count[0],
            "timing_delay": timing_delay,
            "timeout": timeout[0],
        },

        "mode": {
            "timing_delay": 0,
            "timeout": timeout[0],
            "mode": mode,
            "workers_count": 4,
            "sequential_result": sequential_result,
            "parallel_result": parallel_4_result,
        },

        "timeout": {
            "timing_delay": 0,
            "timeout_values": timeout,
            "mode": mode,
            "workers_count": workers_count[0],
        },
    }

    # ---------------------------------------------------------
    # 3. Collect Results
    # ---------------------------------------------------------
    results = {
        "worker": worker_results,
    }

    results.update(
        run_selected_experiments(
            target_test=target_test,
            runs=runs,
            selected_experiments=selected_experiments,
            experiment_configs=experiment_configs,
        )
    )

    return results

if __name__ == "__main__":

    target_test = "flaky_repro/examples/functional_validation/test_timing_flaky.py::test_timing_behavior"
    runs = 5

    workers_count = [2, 4, 8]
    timing_delay = [10, 20, 50]
    timeout = [5, 10, 20]
    mode = "Parallel"

    result = run_initial_investigation(
        target_test=target_test,
        runs=runs,
        mode=mode,
        workers_count=workers_count,
        timing_delay=timing_delay,
        timeout=timeout
    )

    print("\n" + "=" * 60)
    print("        INITIAL INVESTIGATION TEST")
    print("=" * 60)

    print("\n--- WORKER EXPERIMENTS ---")
    for experiment in result["worker"]:
        print(
            f"Workers: {experiment['worker']} | "
            f"Failure Rate: {experiment['result']['failure_rate']}%"
        )

    print("\n--- TIMING EXPERIMENTS ---")
    for experiment in result["timing"]:
        print(
            f"Delay: {experiment['timing_delay']} ms | "
            f"Failure Rate: {experiment['result']['failure_rate']}%"
        )

    print("\n--- MODE EXPERIMENTS ---")
    for experiment in result["mode"]:
        print(
            f"Mode: {experiment['mode']} | "
            f"Workers: {experiment['workers']} | "
            f"Failure Rate: {experiment['result']['failure_rate']}%"
        )

    print("\n--- TIMEOUT EXPERIMENTS ---")
    for experiment in result["timeout"]:
        print(
            f"Timeout: {experiment['timeout']}s | "
            f"Failure Rate: {experiment['result']['failure_rate']}%"
        )

    print("\n" + "=" * 60)
    print("        INITIAL INVESTIGATION COMPLETE")
    print("=" * 60)