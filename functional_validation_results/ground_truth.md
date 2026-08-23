# Ground Truth Metadata for Flaky-Repro Functional Validation

---

## Test 1: Timing Sensitive

* **Test**: `examples/functional_validation/test_timing_validation.py::test_timing_sensitive`
* **Mechanism**: CPU scheduling and thread spawn contention.
* **Known influencing factor**: Timing delay.
* **Expected direction**: Spacings between subprocess spawns (larger delay) $\rightarrow$ lower failure rate (reduced contention).
* **Expected candidate**: `timing_delay` (e.g. 10ms or 20ms).
* **Expected reproduction difficulty**: Hard (CPU load and scheduling contention are highly variable across execution runs).
* **Expected limitations**: Python `ThreadPoolExecutor` concurrent execution sleeps threads in parallel, so `timing_delay` inside parallel threads does not stagger process starts.

---

## Test 2: Worker Sensitive

* **Test**: `examples/functional_validation/test_worker_validation.py::test_worker_sensitive`
* **Mechanism**: Shared state file access overlap.
* **Known influencing factor**: Worker count.
* **Expected direction**: Higher worker count $\rightarrow$ higher concurrency overlap $\rightarrow$ higher failure rate.
* **Expected candidate**: `worker` (e.g. worker count 4 or 8).
* **Expected reproduction difficulty**: Easy/Medium.
* **Expected limitations**: File lock or file read-write speeds can introduce environment-specific failure rate plateaus.

---

## Test 3: Execution Mode Sensitive

* **Test**: `examples/functional_validation/test_mode_validation.py::test_mode_sensitive`
* **Mechanism**: Shared file state concurrency overlap.
* **Known influencing factor**: Execution mode (Sequential vs Parallel).
* **Expected direction**: Parallel $\rightarrow$ flaky/failing; Sequential $\rightarrow$ stably passing (0% failure rate).
* **Expected candidate**: `mode` (Parallel).
* **Expected reproduction difficulty**: Easy.
* **Expected limitations**: None.

---

## Test 4: Timing + Worker Interaction

* **Test**: `examples/functional_validation/test_multifactor_validation.py::test_timing_worker_interaction`
* **Mechanism**: Inter-test startup delay (delta) sensing on a shared file.
* **Known influencing factor**: Concurrency mode + Timing delay.
* **Expected direction**:
  * Sequential $\rightarrow$ Stable/Passing (delta > 0.2s).
  * Parallel with no delay $\rightarrow$ Low flakiness (~20% failure rate, delta < 0.005s).
  * Parallel with timing delay $\rightarrow$ High flakiness (100% failure rate, 0.005s <= delta <= 0.08s).
* **Expected candidate**: Interactive timing + worker condition.
* **Expected reproduction difficulty**: Hard.
* **Expected limitations**: Flaky-Repro analyzes candidates independently (single factor at a time). It has no multi-factor interaction ranking or confirmation built into its engine. It will likely confirm individual factors (like timing_delay) without capturing the intersection cleanly.

---

## Test 5: Pure Random Flakiness

* **Test**: `examples/functional_validation/test_random_validation.py::test_random_flaky`
* **Mechanism**: Independent probabilistic coin-flip (`random.random()`).
* **Known influencing factor**: None.
* **Expected direction**: Consistent ~30% failure rate across all configurations.
* **Expected candidate**: None (all candidates should be weak or rejected).
* **Expected reproduction difficulty**: Easy (statistically).
* **Expected limitations**: Small sample sizes (10 runs per experiment) can cause statistical noise, leading to false positive candidate confirmations.

---

## Test 6: Stable Control

* **Test**: `examples/functional_validation/test_stable_validation.py::test_stable`
* **Mechanism**: Trivial assertion (`assert True`).
* **Known influencing factor**: None.
* **Expected direction**: Always passing (0% failure rate).
* **Expected candidate**: None.
* **Expected reproduction difficulty**: N/A.
* **Expected limitations**: None.
