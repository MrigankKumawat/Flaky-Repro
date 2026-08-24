# Flaky-Repro

**An empirical, frequency-based flaky test diagnosis and reproduction tool for pytest.**

Flaky-Repro investigates flaky tests by repeatedly executing them under different execution conditions, measuring failure frequencies, identifying stronger failure-associated conditions, confirming those candidates through repeated experiments, and attempting to reproduce the observed behavior.

---

##  Why Flaky-Repro?

Flaky tests are difficult to diagnose because they can pass and fail under seemingly identical conditions.

A simple approach is to repeatedly run a test:

```bash
pytest test_example.py::test_something
```

But repeated execution alone does not tell you which execution condition is associated with the failures.

Flaky-Repro takes an empirical approach.

Instead of only asking:

> Does this test fail sometimes?

Flaky-Repro investigates:

> Under which execution conditions does this test fail more frequently, and can that behavior be reproduced?

---

##  Installation

Install Flaky-Repro directly from PyPI:

```bash
pip install flaky-repro
```

Verify the installation:

```bash
flaky-repro --version
```

Expected:

```text
flaky-repro 0.1.0
```

---

##  Quick Start

Run Flaky-Repro against a pytest target:

```bash
flaky-repro <pytest-target>
```

For example:

```bash
flaky-repro flaky_repro/examples/functional_validation/test_worker_validation.py::test_worker_sensitive
```

Flaky-Repro will automatically run the target through its diagnosis and reproduction pipeline.

---

##  How It Works

Flaky-Repro follows a multi-stage empirical diagnosis process:

```text
                         Pytest Target
                              │
                              ▼
                     ┌────────────────┐
                     │    Baseline    │
                     └───────┬────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │    Investigation     │
                  │                      │
                  │ • Worker counts      │
                  │ • Execution modes    │
                  │ • Timing conditions  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Candidate Detection  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │     Confirmation     │
                  │                      │
                  │ Repeated candidate  │
                  │ observations         │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │     Reproduction     │
                  │                      │
                  │ Higher-volume runs  │
                  └──────────┬───────────┘
                             │
                             ▼
                       Diagnostic Result
```

The goal is not simply to rerun a test.

The goal is to determine whether specific execution conditions are associated with increased failure frequency and whether those conditions can be reproduced consistently.

---

##  What It Investigates

Flaky-Repro can investigate conditions such as:

- Worker/concurrency levels
- Sequential vs parallel execution
- Timing delays
- Failure frequency under different conditions
- Candidate strength
- Candidate consistency
- Reproduction consistency

The tool compares observed failure rates across conditions and ranks candidates based on their observed signals.

---

##  Example

The following output comes from the included worker-concurrency validation test.

### Result

```text
============================================================
                        FLAKY-REPRO
============================================================

TEST
------------------------------------------------------------
Target : flaky_repro\examples\functional_validation\test_worker_validation.py::test_worker_sensitive

RESULT
------------------------------------------------------------
Status               : FLAKY
Observed Pattern     : Parallel Execution
Strongest Signal     : Worker Count
Condition            : 8 workers
Reproduction         : REPRODUCED
```

### Baseline

The test passed consistently under the sequential baseline:

```text
Baseline
  Runs         : 20
  Passed       : 20
  Failed       : 0
  Failure Rate : 0%
```

### Candidate

Under the strongest candidate condition:

```text
Candidate
  Condition    : Worker (8 workers)
  Runs         : 20
  Passed       : 13
  Failed       : 7
  Failure Rate : 35%
```

The observed failure-rate difference was:

```text
Effect
  Failure delta: +35 pp
  Direction    : Increased
```

### Investigation

```text
Type           Condition                 Failure Rate
------------------------------------------------------------
Worker         2 workers                 5%
Worker         4 workers                 30%
Worker         8 workers                 35%
Timing         10 ms                     5%
Timing         20 ms                     10%
Mode           Sequential                0%
Mode           Parallel / 4              30%
```

### Candidate Ranking

```text
Rank   Candidate                    Failure Rate   Signal
------------------------------------------------------------
#1     Worker (8 workers)           35%            STRONG
#2     Worker (4 workers)           30%            STRONG
#3     Timing (20 ms)               10%            STRONG
```

### Confirmation

Candidates are repeatedly evaluated to determine whether the observed effect persists:

```text
Candidate                      Classification        Consistency
-----------------------------------------------------------------
#1 Worker (8 workers)          REPEATEDLY OBSERVED   100.0%
#2 Worker (4 workers)          REPEATEDLY OBSERVED   100.0%
#3 Timing (20 ms)              REPEATEDLY OBSERVED   100.0%
```

### Reproduction

The strongest candidates are then subjected to higher-volume reproduction runs:

```text
Rank   Candidate                  Repetitions   Consistency    Result
-----------------------------------------------------------------------
#1     Worker (8 workers)         3             100.0%         REPRODUCED
#2     Worker (4 workers)         3             100.0%         REPRODUCED
#3     Timing (20 ms)             3             100.0%         REPRODUCED
```

### Interpretation

In this example:

- The test passed consistently under the sequential baseline.
- Parallel execution increased the observed failure rate.
- The 8-worker configuration produced the strongest observed signal.
- The candidate remained consistent during confirmation.
- The behavior was successfully reproduced during the reproduction stage.

This demonstrates how Flaky-Repro moves from **observation → investigation → candidate detection → confirmation → reproduction**.

---

##  CLI Usage

### Show help

```bash
flaky-repro --help
```

or:

```bash
flaky-repro -h
```

### Show version

```bash
flaky-repro --version
```

or:

```bash
flaky-repro -V
```

### Run a test

```bash
flaky-repro <pytest-target>
```

Example:

```bash
flaky-repro tests/test_concurrency.py::test_sensitive
```

---

##  Included Validation Examples

The repository includes functional validation tests designed to exercise different flaky-test behaviors, including:

- Worker/concurrency behavior
- Timing behavior
- Sequential vs parallel execution
- Stable tests
- Random/flaky behavior
- Multifactor conditions

These examples are useful for understanding and validating the diagnostic pipeline.

---

##  Safety & Limitations

Flaky-Repro repeatedly executes the target test under multiple configurations.

**Only run it against tests and environments where repeated execution is safe and side effects are acceptable.**

Be especially careful with tests that:

- Modify production data
- Send emails or messages
- Perform financial transactions
- Create irreversible external side effects
- Depend on shared external state
- Interact with rate-limited services

### Important

Flaky-Repro is an **empirical diagnostic tool**.

Its conclusions are based on observed execution frequencies and repeated experiments.

A strong signal means that a condition was associated with an increased failure rate in the observed experiments. It should not automatically be interpreted as definitive proof of the underlying root cause.

---

##  Project Status

**Current version: `0.1.1`**

The `0.1.1` release provides:

- PyPI packaging
- Command-line interface
- Baseline execution
- Multi-condition investigation
- Candidate detection
- Candidate confirmation
- Reproduction testing
- Human-readable diagnostic output
- Functional validation examples

The project is currently an early release, and future versions may change diagnostic behavior, internal APIs, configuration options, and output formats.

---

##  Development

Clone the repository and enter the project directory:

```bash
git clone https://github.com/MrigankKumawat/Flaky-Repro.git
cd Flaky-Repro
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the project in editable mode:

```bash
pip install -e .
```

---

##  License

Flaky-Repro is released under the MIT License.

See the `LICENSE` file for the complete license text.

---

##  Contributing

Issues, bug reports, suggestions, and improvements are welcome.

If you discover a flaky-test pattern that Flaky-Repro handles incorrectly, opening an issue with a reproducible example can help improve the project.

---

##  Flaky-Repro

**Investigate the conditions behind flaky tests.**
