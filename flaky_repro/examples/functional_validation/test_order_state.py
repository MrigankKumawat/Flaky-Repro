import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "_order_state.flag")

def test_setup_changes_state():
    """State-changing setup test. Always passes."""
    with open(STATE_FILE, "w") as f:
        f.write("changed")

def test_target_depends_on_state():
    """
    Fails if the shared-state flag is present (i.e. the setup test
    ran immediately before this one in the same sequence); passes
    when run alone, since no flag file exists yet.
    """
    state_was_changed = os.path.exists(STATE_FILE)
    if state_was_changed:
        os.remove(STATE_FILE)  # reset so the next invocation starts clean
    assert not state_was_changed, "target test ran after state-changing setup"