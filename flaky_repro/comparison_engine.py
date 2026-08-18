import statistics

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

    if baseline_failure_rate !=0 :
        relative_change = round(((experiment_failure_rate - baseline_failure_rate)/ baseline_failure_rate) * 100, 2)
    else:
        relative_change = None

    failure_count_delta = experiment_failed - baseline_failed

    baseline_pass_rate = baseline_passed/baseline_total_runs * 100
    experiment_pass_rate = experiment_passed/experiment_total_runs * 100
    pass_rate_delta = experiment_pass_rate - baseline_pass_rate

    if experiment_failure_rate > baseline_failure_rate:
        direction = "Increased"
    elif experiment_failure_rate < baseline_failure_rate:
        direction = "Decreased"
    else:
        direction = "Unchanged"


    return {
        "baseline": {
            "total_runs": baseline_total_runs,
            "passed": baseline_passed,
            "failed": baseline_failed,
            "failure_rate": baseline_failure_rate
        },

        "experiment": {
            "total_runs": experiment_total_runs,
            "passed": experiment_passed,
            "failed": experiment_failed,
            "failure_rate": experiment_failure_rate
        },

        "comparison": {
            "failure_rate_delta": failure_rate_delta,
            "relative_change": relative_change,
            "failure_count_delta":failure_count_delta,
            "pass_rate_delta":pass_rate_delta,
            "direction": direction
        }
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

def ranking_engine(comparison_results: list):
    if not comparison_results:
        return None

    strongest_delta = max(
        comparison_results,
        key=lambda x: x["comparison"]["comparison"]["failure_rate_delta"]
    )

    return strongest_delta

def compare_repeated_observations(baseline_results, observations):
    if not observations:
        return None

    all_comparisons = []

    for i, observation in enumerate(observations, start=1):
        result = compare_results(baseline_results, observation)

        all_comparisons.append({
            "observation_index": i,
            "comparison": result["comparison"]
        })

    return all_comparisons

def extract_effects(comparison_results:list):
    failure_rate_list = []

    if not comparison_results:
        return None

    for comparison in comparison_results:
        failure_rate = comparison["comparison"]["failure_rate_delta"]
        failure_rate_list.append(failure_rate)

    return failure_rate_list
    

def analyze_consistency(effects: list):
    if not effects:
        return None

    total_effect = 0
    for effect in effects:
        total_effect += effect

    mean_effect = total_effect / len(effects)
    min_effect = min(effects)
    max_effect = max(effects)
    effect_range = max_effect - min_effect

    if len(effects) >= 2:
        standard_deviation = round(statistics.stdev(effects), 2)
    else:
        standard_deviation = None

    if mean_effect == 0 or standard_deviation is None:
        coefficient_variation = None
    else:
        coefficient_variation = round(
            standard_deviation / abs(mean_effect), 2
        )

    return {
        "observation_count": len(effects),
        "mean_effect": round(mean_effect, 2),
        "min_effect": min_effect,
        "max_effect": max_effect,
        "effect_range": round(effect_range, 2),
        "standard_deviation": standard_deviation,
        "coefficient_variation": coefficient_variation,
    }

def build_evidence_summary(comparison_result, consistency_result):
    return{
        "effect":{
            "failure_rate_delta": comparison_result['failure_rate_delta'],
            "relative_change":comparison_result['relative_change'],
            "failure_count_delta":comparison_result['failure_count_delta'],
            "pass_rate_delta":comparison_result['pass_rate_delta'],
            "direction":comparison_result['direction']
        },
        "consistency":{
            "observation_count":consistency_result['observation_count'],
            "mean_effect":consistency_result['mean_effect'],
            "min_effect":consistency_result['min_effect'],
            "max_effect":consistency_result['max_effect'],
            "effect_range":consistency_result['effect_range'],
            "standard_deviation":consistency_result['standard_deviation'],
            "coefficient_variation":consistency_result['coefficient_variation']
        }
    }