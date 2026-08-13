import time
import random


def test_timing_behavior():
    start = time.time()

    # Simulate an operation with variable execution time
    time.sleep(random.uniform(0.01, 0.08))
    time.sleep()
    elapsed = time.time() - start

    # Sometimes the operation will exceed this threshold
    assert elapsed < 0.05