def compare_results(baseline_results, experiment_results):
    baseline_total_runs = baseline_results['total_runs']
    baseline_passed = baseline_results['passed']
    baseline_failed = baseline_results['failed']
    baseline_failure_rate = baseline_results['failure_rate']

    experiment_total_runs = experiment_results['total_runs']
    experiment_passed = experiment_results['passed']
    experiment_failed = experiment_results['failed']
    experiment_failure_rate = experiment_results['failure_rate']

    failure_rate_delta = experiment_failure_rate - baseline_failure_rate

    relative_change = ((experiment_failure_rate - baseline_failure_rate)/ baseline_failure_rate) * 100 if baseline_failure_rate != 0 else None

    return { 
        "delta_change":failure_rate_delta,
        "relative_change":relative_change
    }

def compare_experiments(baseline_results, experiments:list):
    comparision_results = []
    for experiment in experiments:
        result = compare_results(baseline_results, experiment['result'])
        comparision_results.append({
            "experiment": experiment,
            "comparison": result
        })

    return comparision_results

def ranking_engine(comparison_results:list):
    if not comparison_results:
        return None

    strongest_delta = max(
        comparison_results,
        key=lambda x: x["comparison"]["delta_change"]
    )

    return strongest_delta

print(ranking_engine(comparison_results=[
    {
        "experiment": {
            "worker": 2
        },
        "comparison": {
            "delta_change": 20
        }
    },
    {
        "experiment": {
            "worker": 4
        },
        "comparison": {
            "delta_change": -12
        }
    },
    {
        "experiment": {
            "worker": 8
        },
        "comparison": {
            "delta_change": 22
        }
    }
]))