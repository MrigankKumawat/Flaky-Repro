import random

# Intended Ground Truth:
# Purely probabilistic random flakiness (30% failure rate).
# No real dependency on worker count, timing delay, or execution mode.
# Expected outcome: detected as flaky, but no confirmed candidates (rejected).

def test_random_flaky():
    assert random.random() > 0.30
