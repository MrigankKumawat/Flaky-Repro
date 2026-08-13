import subprocess
import re

target_test = str(input("Enter test file path:")).strip()
runs = int(input("Enter number of test runs:"))

total_runs = 0 
passed = 0
failed = 0
failure_evidence = []

test_name = target_test.split("::")[-1] if "::" in target_test else target_test

for i in range(1,runs+1):
    res = subprocess.run(["pytest", target_test], capture_output=True, text=True)
    total_runs = i
    
    if res.returncode == 0:
        passed+=1
    elif res.returncode == 1:
        failed+=1
        # print("=================== Failure/Error Reasons ===================")
        # print(res.stdout)
    
        line_num = "Unknown"
        assertion_text = "No assertion isolated."
        
        for line in res.stdout.splitlines():
            clean_line = line.strip()
            if clean_line.startswith("E ") and "assert" in clean_line:
                # Strip out the 'E ' prefix and 'assert ' keyword
                assertion_text = re.sub(r"^E\s+assert\s*", "", clean_line).strip()
            
            # Find the line number mapping
            match = re.search(r"\.py:(\d+): AssertionError", clean_line)
            if match:
                line_num = match.group(1)


        failure_evidence.append({
            "number": failed,
            "line": line_num,
            "assertion": assertion_text
        })
    
    failure_rate = (failed/total_runs)*100 
    
    if failure_rate == 0.0:
        rate_classification = "Stable"
    elif failure_rate > 0.0 and failure_rate <= 20.0:
        rate_classification = "Low Flakiness"
    elif failure_rate > 20.0 and failure_rate <= 50.0:
        rate_classification = "Flaky/Moderate"
    elif failure_rate > 50.0 and failure_rate <= 80.0:
        rate_classification = "Highly Flaky"
    elif failure_rate > 80.0 and failure_rate <=100.0:
        rate_classification = "Severely Unstable"
    elif failure_rate == 100.0:
        rate_classification = "Consistently Failing"
        
    
print("============= FLAKY-REPRO =============")
print(f"Total Runs: {total_runs}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Failure Rate: {round(failure_rate, 2)}%")
print(f"Rate Classification:{rate_classification}")

if failure_evidence:
    print("\n------------- Failure Evidence -------------")
    for ev in failure_evidence:
        print(f"\nFailure #{ev['number']}")
        print(f"Line: {ev['line']}")
        print(f"Assertion: {ev['assertion']}")
