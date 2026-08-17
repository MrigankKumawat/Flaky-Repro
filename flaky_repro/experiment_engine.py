from flaky_repro.runner import run_parallel_test
from flaky_repro.runner import run_sequential_test
from flaky_repro.runner import json_experiments

def worker_experiment(target_test:str, runs:int, workers_count:list):
    all_worker_results = []
    
    for worker in workers_count:
        result = run_parallel_test(target_test, runs, worker)
        json_experiments(result, runs, "Parallel",target_test, worker)
        
        all_worker_results.append({
            "worker":worker,
            "result":result
        })
        
    return all_worker_results
        
def timing_experiment(target_test:str, runs:int, mode: str, workers_count:list, timing_values:list):
    all_timing_results = []
    for time_value in timing_values:
        delay = time_value/1000
        
        if mode == "Sequential":
            result = run_sequential_test(target_test, runs, delay)
        elif mode == "Parallel":
            result = run_parallel_test(target_test, runs, workers_count, delay)
            
        all_timing_results.append({
            "timing_delay":time_value,
            "result":result
        })
    
    return all_timing_results
        
def mode_experiment(target_test:str, runs:int, workers_count:int):
    result_sequential = run_sequential_test(target_test, runs, timing_delay=0)
    result_parallel = run_parallel_test(target_test, runs, workers_count, timing_delay=0)
    
    return [
        {
            "mode":"Sequential",
            "workers":1,
            "result":result_sequential
        },
        {
            "mode":"Parallel",
            "workers":workers_count,
            "result":result_parallel
        }
    ]    
        
if __name__ == "__main__":
    target_test = input("Enter test file path: ").strip()
    runs = int(input("Enter number of test runs: ").strip())
    workers = int(input("Enter workers:").strip())
    
    result = mode_experiment(target_test=target_test, runs=runs, workers_count=workers)
    print(result)
    # # Input timing delays
    # raw_timings = input(
    #     "Enter timing delays in ms (e.g., 10, 20, 30): "
    # ).strip()
    # timing_delays = [
    #     int(t.strip()) for t in raw_timings.split(",") if t.strip().isdigit()
    # ]

    # # Run the experiment orchestrator
    # results = timing_experiment(
    #     target_test=target_test,
    #     runs=runs,
    #     mode="Parallel",
    #     workers_count=4,
    #     timing_values=timing_delays,
    # )

    # # Print summary table
    # print("\n============= TIMING EXPERIMENT SUMMARY =============")
    # for entry in results:
    #     delay = entry["timing_delay"]
    #     res = entry["result"]
    #     print(
    #         f"Delay: +{delay:<3}ms | Passed: {res['passed']:<3} | Failed: {res['failed']:<3} | Failure Rate: {res['failure_rate']}% ({res['rate_classification']})"
    #     )
           