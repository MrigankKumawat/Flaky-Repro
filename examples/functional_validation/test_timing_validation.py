import time
import random

# Intended Ground Truth:
# Timing delay is an influencing factor due to CPU/process spawn contention.
# Lower timing delay (0ms) -> higher contention -> higher failure rate.
# Higher timing delay (50ms) -> lower contention -> lower failure rate.

def test_timing_sensitive():
    start = time.time()
    
    # Introduce small CPU contention simulation
    time.sleep(random.uniform(0.01, 0.03))
    time.sleep(0.015)
    
    elapsed = time.time() - start
    
    # Assert elapsed time remains under 0.038 seconds.
    # Contention from zero delay makes it exceed this limit easily.
    assert elapsed < 0.038
