def format_candidate_condition(candidate):
    if not candidate:
        return "N/A"
    ctype = candidate.get("type")
    cond = candidate.get("condition", {})
    if ctype == "worker":
        return f"Worker ({cond.get('worker')} workers)"
    elif ctype == "timing_delay":
        return f"Timing ({cond.get('timing_delay')} ms)"
    elif ctype == "mode":
        return f"Mode ({cond.get('mode')} / {cond.get('workers')})"
    return "Unknown"

def format_pp(val):
    if val is None:
        return "N/A"
    try:
        fval = float(val)
        return f"{fval:+.2f} pp" if not fval.is_integer() else f"{int(fval):+} pp"
    except (ValueError, TypeError):
        return f"{val} pp"

def format_rate(val):
    if val is None:
        return "N/A"
    try:
        fval = float(val)
        return f"{fval:.2f}%" if not fval.is_integer() else f"{int(fval)}%"
    except (ValueError, TypeError):
        return f"{val}%"

# User-facing display labels for confirmation classifications.
# "Confirmed" is an internal classification label only; it does not mean
# root cause has been proven, so it is rendered as evidence-based
# language here. Underlying classification logic is unchanged.
CONFIRMATION_DISPLAY_LABELS = {
    "CONFIRMED": "REPEATEDLY OBSERVED",
}

def format_confirmation_classification(classification):
    label = (classification or "Rejected").upper()
    return CONFIRMATION_DISPLAY_LABELS.get(label, label)

def print_pipeline_result(result):
    print("============================================================")
    print("                        FLAKY-REPRO")
    print("============================================================")

    print("\nWARNING")
    print("------------------------------------------------------------")
    print("Flaky-Repro repeatedly executes the target test under")
    print("multiple configurations.")
    print("")
    print("Run it only against tests/environments where repeated")
    print("execution is safe and side effects are acceptable.")
    print("------------------------------------------------------------")

    # 1. TEST SECTION
    print("\nTEST")
    print("------------------------------------------------------------")
    print(f"Target : {result.get('target_test', 'Unknown')}")

    baseline = result.get("baseline", {})
    baseline_rate = baseline.get("failure_rate", 0.0)

    # Status
    confirmed = result.get("confirmed_candidates", [])
    if confirmed or baseline_rate > 0.0:
        status = "FLAKY"
    else:
        status = "STABLE"

    # Strongest observed condition (evidence-based; not a proven root cause)
    if confirmed:
        top_confirmed = confirmed[0]["candidate"]
        ctype = top_confirmed.get("type")
        cond = top_confirmed.get("condition", {})
        if ctype == "worker":
            cause = "Worker Count"
            condition_str = f"{cond.get('worker')} workers"
        elif ctype == "timing_delay":
            cause = "Timing Delay"
            condition_str = f"{cond.get('timing_delay')} ms"
        elif ctype == "mode":
            cause = "Execution Mode"
            condition_str = f"{cond.get('mode')} ({cond.get('workers')} workers)"
        else:
            cause = "Unknown"
            condition_str = "N/A"
    else:
        cause = "None Detected"
        condition_str = "N/A"

    # Reproduction details
    reproductions = result.get("candidate_reproductions", [])
    if reproductions:
        top_repro = reproductions[0]
        repro_class = top_repro.get("reproduction_classification", {})
        repro_status = repro_class.get("classification", "NOT_REPRODUCED")
    else:
        repro_status = "NOT_REPRODUCED" if (confirmed or baseline_rate > 0.0) else "N/A"

    # 2. RESULT SECTION
    print("\nRESULT")
    print("------------------------------------------------------------")
    print(f"Status               : {status}")
    print(f"Strongest Condition  : {cause}")
    print(f"Condition            : {condition_str}")
    print(f"Reproduction         : {repro_status}")

    # 3. EVIDENCE SECTION
    print("\nEVIDENCE")
    print("------------------------------------------------------------")
    
    # Baseline evidence
    print("Baseline")
    print(f"  Runs         : {baseline.get('total_runs', 0)}")
    print(f"  Passed       : {baseline.get('passed', 0)}")
    print(f"  Failed       : {baseline.get('failed', 0)}")
    print(f"  Failure Rate : {format_rate(baseline_rate)}")
    print("")

    # Top Candidate / Confirmed Candidate evidence
    candidates_data = result.get("candidates", {})
    ranked_candidates = candidates_data.get("ranked", [])
    
    top_candidate = None
    if confirmed:
        top_candidate = confirmed[0]["candidate"]
    elif ranked_candidates:
        top_candidate = ranked_candidates[0]

    if top_candidate:
        cand_res = top_candidate.get("result", {})
        cand_effect = top_candidate.get("effect", {})
        comp = cand_effect.get("comparison", {})
        
        cand_cond_str = format_candidate_condition(top_candidate)
        cand_runs = cand_res.get("total_runs", 0)
        cand_passed = cand_res.get("passed", 0)
        cand_failed = cand_res.get("failed", 0)
        cand_rate = format_rate(cand_res.get("failure_rate", 0.0))
        
        delta = comp.get("failure_rate_delta", 0.0)
        direction = comp.get("direction", "Unchanged")
        
        print("Candidate")
        print(f"  Condition    : {cand_cond_str}")
        print(f"  Runs         : {cand_runs}")
        print(f"  Passed       : {cand_passed}")
        print(f"  Failed       : {cand_failed}")
        print(f"  Failure Rate : {cand_rate}")
        print("")
        print("Effect")
        print(f"  Failure delta: {format_pp(delta)}")
        print(f"  Direction    : {direction}")
    else:
        print("Candidate")
        print("  Condition    : N/A")
        print("  Runs         : N/A")
        print("  Passed       : N/A")
        print("  Failed       : N/A")
        print("  Failure Rate : N/A")
        print("")
        print("Effect")
        print("  Failure delta: N/A")
        print("  Direction    : N/A")

    # 4. INVESTIGATION SECTION
    print("\nINVESTIGATION")
    print("------------------------------------------------------------")
    print(f"{'Type':<14} {'Condition':<25} {'Failure Rate':<12}")
    print("------------------------------------------------------------")
    
    investigation = result.get("investigation", {})
    
    # Worker runs
    for item in investigation.get("worker_experiment", []):
        worker = item.get("worker")
        rate = format_rate(item.get("result", {}).get("failure_rate", 0.0))
        print(f"{'Worker':<14} {f'{worker} workers':<25} {rate:<12}")
        
    # Timing runs
    for item in investigation.get("timing_experiment", []):
        delay = item.get("timing_delay")
        rate = format_rate(item.get("result", {}).get("failure_rate", 0.0))
        print(f"{'Timing':<14} {f'{delay} ms':<25} {rate:<12}")
        
    # Mode runs
    for item in investigation.get("mode_experiment", []):
        mode_val = item.get("mode")
        workers = item.get("workers")
        rate = format_rate(item.get("result", {}).get("failure_rate", 0.0))
        if mode_val == "Sequential":
            cond_str = "Sequential"
        else:
            cond_str = f"Parallel / {workers}"
        print(f"{'Mode':<14} {cond_str:<25} {rate:<12}")

    # 5. CANDIDATES SECTION
    print("\nCANDIDATES")
    print("------------------------------------------------------------")
    print(f"{'Rank':<6} {'Candidate':<28} {'Failure Rate':<14} {'Signal':<12}")
    print("------------------------------------------------------------")
    top_candidates = result.get("candidates", {}).get("top", [])
    for i, cand in enumerate(top_candidates, 1):
        cand_str = format_candidate_condition(cand)
        fail_rate = format_rate(cand.get("result", {}).get("failure_rate", 0.0))
        signal = cand.get("classification", "NO_SIGNAL")
        print(f"{f'#{i}':<6} {cand_str:<28} {fail_rate:<14} {signal:<12}")

    # 6. CONFIRMATION SECTION
    print("\nCONFIRMATION")
    print("------------------------------------------------------------")
    print(f"{'Candidate':<30} {'Classification':<21} {'Consistency':<14} {'Avg Effect':<12}")
    print("------------------------------------------------------------")
    confirmations = result.get("candidate_confirmations", [])
    for i, record in enumerate(confirmations, 1):
        cand = record.get("candidate")
        cand_str = format_candidate_condition(cand)
        cand_desc = f"#{i} {cand_str}"
        
        confirm = record.get("confirmation", {})
        classification = format_confirmation_classification(confirm.get("classification", "Rejected"))
        consistency = f"{confirm.get('consistency_rate', 0.0)}%"
        effect = format_pp(confirm.get("average_effect", 0.0))
        
        print(f"{cand_desc:<30} {classification:<21} {consistency:<14} {effect:<12}")
    if not confirmations:
        print(f"{'N/A':<30} {'N/A':<21} {'N/A':<14} {'N/A':<12}")

    # 7. REPRODUCTION SECTION
    print("\nREPRODUCTION")
    print("------------------------------------------------------------")
    print(f"{'Rank':<6} {'Candidate':<26} {'Repetitions':<13} {'Consistency':<14} {'Avg Effect':<13} {'Result':<12}")
    print("------------------------------------------------------------")
    if reproductions:
        for i, cand in enumerate(top_candidates, 1):
            cand_str = format_candidate_condition(cand)
            
            repro = None
            for r in reproductions:
                if r.get("candidate") == cand:
                    repro = r
                    break
            
            if repro:
                repro_class = repro.get("reproduction_classification", {})
                repro_runs = repro_class.get("total_repetitions", 0)
                consistency = f"{repro_class.get('consistency_rate', 0.0)}%"
                effect = format_pp(repro_class.get("average_effect", 0.0))
                status = repro_class.get("classification", "NOT_REPRODUCED")
            else:
                # Determine confirmation status
                is_confirmed = False
                for conf in confirmations:
                    if conf.get("candidate") == cand:
                        if conf.get("confirmation", {}).get("classification") == "Confirmed":
                            is_confirmed = True
                        break
                repro_runs = "N/A"
                consistency = "N/A"
                effect = "N/A"
                status = "NOT_RUN" if is_confirmed else "REJECTED"
                
            print(f"{f'#{i}':<6} {cand_str:<26} {repro_runs:<13} {consistency:<14} {effect:<13} {status:<12}")
    else:
        print(f"{'N/A':<6} {'N/A':<26} {'N/A':<13} {'N/A':<14} {'N/A':<13} {'N/A':<12}")

    print("\n============================================================")
    print("                    INVESTIGATION COMPLETE")
    print("============================================================")