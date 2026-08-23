import os
import time

# Intended Ground Truth:
# Sequential -> passes stably (concurrency = 1)
# Parallel -> flaky/failing (concurrency > 1)

def test_mode_sensitive():
    filepath = "mode_concurrency.txt"
    try:
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                f.write("0")

        for _ in range(5):
            try:
                with open(filepath, "r") as f:
                    content = f.read().strip()
                    count = int(content) if content else 0
                with open(filepath, "w") as f:
                    f.write(str(count + 1))
                break
            except Exception:
                time.sleep(0.005)
        else:
            assert False

        time.sleep(0.04)

        for _ in range(5):
            try:
                with open(filepath, "r") as f:
                    content = f.read().strip()
                    final_count = int(content) if content else 0
                break
            except Exception:
                time.sleep(0.005)
        else:
            final_count = count + 1

        for _ in range(5):
            try:
                with open(filepath, "w") as f:
                    f.write(str(max(final_count - 1, 0)))
                break
            except Exception:
                time.sleep(0.005)

        concurrency = final_count - count
        assert concurrency <= 1
    except Exception:
        assert False
