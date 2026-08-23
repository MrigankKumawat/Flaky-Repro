# Flaky-Repro

Flaky-Repro is an empirical, frequency-based tool designed to diagnose and reproduce flaky tests under varying execution conditions (such as concurrency worker counts, mode configurations, and timing delays).

It is designed to help developers identify the specific runtime factors associated with test flakiness, helping speed up troubleshooting and reduce debugging frustration.

> [!WARNING]
> **Safety Warning**: Flaky-Repro repeatedly executes target tests under parallel and timing-delayed environments. Only run it against tests and environments where repeated executions are safe and side effects are acceptable.

---

## Why Use Flaky-Repro?
Diagnosing flaky tests is notoriously difficult because they often pass during local sequential runs but fail under high-concurrency CI environments. Flaky-Repro automates the process of executing tests under systematic variations to isolate candidate patterns (such as concurrency levels or timing conditions) and repeats them to confirm and reproduce the failure rate pattern.

*Disclaimer: Flaky-Repro is an empirical tool. It does not mathematically prove a root cause; it ranks conditions based on the statistical difference in failure rates.*

---

## Installation

You can install Flaky-Repro locally from its built wheel:

```bash
pip install flaky_repro
```

*Required dependencies*: `pytest` (>= 7.0.0).

---

## Usage

After installation, invoke the tool directly from your command line.

To run the bundled worker-sensitive validation example:
```bash
flaky-repro
```

To run against your own target test:
```bash
flaky-repro <target-test-path>
```

For example:
```bash
flaky-repro tests/test_my_code.py::test_concurrency
```

---

## MVP Limitations
* Currently optimized for Python environments running `pytest`.
* Executes tests sequentially during baseline checks, and parallelizes using thread-level concurrency during investigation and reproduction stages.
* Relies on process-level isolation for executing each test case.
