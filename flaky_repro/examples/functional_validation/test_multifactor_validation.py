import os
import time
import random

# Intended Ground Truth:
# Sequential + low/no delay -> stable (delta > 0.2) -> passes
# Parallel + low/no delay -> somewhat flaky (delta < 0.005) -> 20-30% flaky failure
# Parallel + timing delay -> significantly more flaky (0.005 < delta < 0.08) -> 100% failure

def test_timing_worker_interaction():
    filepath = "multifactor_concurrency.txt"
    now = time.time()
    delta = 999.0

    if os.path.exists(filepath):
        for _ in range(5):
            try:
                with open(filepath, "r") as f:
                    content = f.read().strip()
                    last_time = float(content) if content else now
                delta = now - last_time
                break
            except Exception:
                time.sleep(0.005)

    for _ in range(5):
        try:
            with open(filepath, "w") as f:
                f.write(str(now))
            break
        except Exception:
            time.sleep(0.005)

    # Sequential execution (delta is large because starting a new pytest subprocess takes time)
    if delta >= 0.20:
        assert True
    else:
        # Parallel execution detected
        # Timing delay staggers test starts by the timing delay (e.g. 10ms - 50ms = 0.01s - 0.05s)
        if 0.005 <= delta <= 0.08:
            assert False  # Highly flaky under parallel + timing delay
        else:
            # Parallel but no delay (spawned as fast as possible, delta < 0.005)
            # Somewhat flaky (approx 20% failure probability)
            assert random.random() > 0.20
