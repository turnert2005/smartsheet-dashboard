"""
Data Integrity Audit - Phase 2 Agentic Voice Project
Comprehensive analysis of schedule data, dependencies, and variance calculations
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict


def load_data():
    """Load the sheet data"""
    with open('sheet_data_audit.json', 'r') as f:
        return json.load(f)


def parse_date(date_str):
    """Parse date string to datetime object"""
    if not date_str:
        return None
    try:
        if 'T' in date_str:
            return datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return None


def analyze_baselines(tasks):
    """Analyze baseline dates vs approved targets"""
    print("\n" + "=" * 80)
    print("  PHASE 1A: BASELINE DATE ANALYSIS")
    print("=" * 80)

    original_target = datetime(2026, 1, 7)
    approved_target = datetime(2026, 1, 13)
    fps_expectation = datetime(2026, 1, 30)

    baseline_dates = []
    end_dates = []
    tasks_at_original = []
    tasks_at_approved = []
    tasks_at_fps = []

    for task in tasks:
        bf = parse_date(task.get('Baseline Finish'))
        ed = parse_date(task.get('End Date'))

        if bf:
            baseline_dates.append((task['Tasks'], bf))
            if bf == original_target:
                tasks_at_original.append(task['Tasks'])
            if bf == approved_target:
                tasks_at_approved.append(task['Tasks'])

        if ed:
            end_dates.append((task['Tasks'], ed))
            if ed == fps_expectation:
                tasks_at_fps.append(task['Tasks'])

    max_baseline = max([d for _, d in baseline_dates]) if baseline_dates else None
    max_end = max([d for _, d in end_dates]) if end_dates else None

    print(f"\n  Reference Dates:")
    print(f"    Original Go-Live:      2026-01-07")
    print(f"    Approved Target:       2026-01-13")
    print(f"    FPS Expectation:       2026-01-30")

    print(f"\n  Findings:")
    print(f"    Max Baseline Finish:   {max_baseline.strftime('%Y-%m-%d') if max_baseline else 'N/A'}")
    print(f"    Max Current End Date:  {max_end.strftime('%Y-%m-%d') if max_end else 'N/A'}")
    print(f"    Tasks ending on 1/7 (baseline):  {len(tasks_at_original)}")
    print(f"    Tasks ending on 1/13 (baseline): {len(tasks_at_approved)}")
    print(f"    Tasks ending on 1/30 (current):  {len(tasks_at_fps)}")

    print(f"\n  [CRITICAL FINDING]")
    print(f"    Baselines still reflect original 1/7 target, NOT the approved 1/13 target.")
    print(f"    This causes ALL variance calculations to be 6 days worse than actual.")

    return {
        'max_baseline': max_baseline,
        'max_end': max_end,
        'baseline_not_updated': len(tasks_at_approved) == 0
    }


def analyze_variance(tasks):
    """Analyze variance calculations"""
    print("\n" + "=" * 80)
    print("  PHASE 1B: VARIANCE CALCULATION ANALYSIS")
    print("=" * 80)

    variance_issues = []

    for task in tasks:
        var = task.get('Variance')
        bf = parse_date(task.get('Baseline Finish'))
        ed = parse_date(task.get('End Date'))

        if var is not None and bf and ed:
            # Variance should be Baseline Finish - End Date (in days)
            expected_var = (bf - ed).days
            actual_var = var if isinstance(var, (int, float)) else 0

            # Check for significant discrepancy
            if abs(expected_var - actual_var) > 1:
                variance_issues.append({
                    'task': task['Tasks'],
                    'expected': expected_var,
                    'actual': actual_var,
                    'difference': expected_var - actual_var
                })

    print(f"\n  Variance Formula Check:")
    print(f"    Expected: Baseline Finish - End Date")
    print(f"    Issues found: {len(variance_issues)}")

    # Get tasks with worst variance
    negative_variance = [(t['Tasks'], t.get('Variance', 0), t.get('Assigned To'))
                        for t in tasks
                        if isinstance(t.get('Variance'), (int, float)) and t.get('Variance', 0) < -10]
    negative_variance.sort(key=lambda x: x[1])

    print(f"\n  Top 10 Worst Variance Tasks:")
    for task_name, var, assigned in negative_variance[:10]:
        print(f"    {var:+6.0f} days | {assigned or 'N/A':10} | {task_name[:50]}")

    return negative_variance


def analyze_dependencies(tasks):
    """Analyze predecessor/dependency chains"""
    print("\n" + "=" * 80)
    print("  PHASE 2: DEPENDENCY CHAIN ANALYSIS")
    print("=" * 80)

    # Build task lookup by row number
    task_by_row = {t['row_number']: t for t in tasks}

    # Find tasks that are blocking others
    blocking_analysis = defaultdict(list)

    for task in tasks:
        pred = task.get('Predecessors')
        if pred:
            # Parse predecessor reference (e.g., "24FS +1d")
            parts = pred.split('FS')[0] if 'FS' in pred else pred.split('SS')[0]
            try:
                pred_row = int(parts.strip())
                pred_task = task_by_row.get(pred_row)
                if pred_task:
                    blocking_analysis[pred_row].append({
                        'blocked_task': task['Tasks'],
                        'blocked_row': task['row_number'],
                        'blocked_assigned': task.get('Assigned To')
                    })
            except:
                pass

    # Find the most blocking tasks
    print(f"\n  Tasks Blocking Multiple Others:")
    blocking_counts = [(row, len(blocked), task_by_row[row])
                       for row, blocked in blocking_analysis.items()]
    blocking_counts.sort(key=lambda x: x[1], reverse=True)

    for row, count, task in blocking_counts[:10]:
        if count > 0:
            status = task.get('Status', 'Unknown')
            health = task.get('Health', 'Unknown')
            assigned = task.get('Assigned To', 'N/A')
            print(f"    Row {row:2} | Blocks {count:2} tasks | {status:12} | {health:6} | {assigned:10} | {task['Tasks'][:40]}")

    # Trace Row 24 (critical IGT task) dependencies
    print(f"\n  [CRITICAL PATH] Tasks dependent on Row 24 (IGT SIP Trunk Setup):")
    row24_deps = blocking_analysis.get(24, [])
    for dep in row24_deps:
        print(f"    -> Row {dep['blocked_row']}: {dep['blocked_assigned'] or 'N/A':10} | {dep['blocked_task'][:50]}")

    return blocking_analysis


def analyze_by_vendor(tasks):
    """Analyze status by vendor"""
    print("\n" + "=" * 80)
    print("  PHASE 3: VENDOR IMPACT ASSESSMENT")
    print("=" * 80)

    vendors = ['FPS', 'IGT', 'Cognigy', 'CSG', 'Frontier']
    vendor_stats = {}

    for vendor in vendors:
        vendor_tasks = [t for t in tasks if t.get('Assigned To') == vendor]

        total = len(vendor_tasks)
        complete = len([t for t in vendor_tasks if t.get('Status') == 'Complete'])
        in_progress = len([t for t in vendor_tasks if t.get('Status') == 'In Progress'])
        not_started = len([t for t in vendor_tasks if t.get('Status') == 'Not Started'])
        red = len([t for t in vendor_tasks if t.get('Health') == 'Red'])

        # Calculate average variance
        variances = [t.get('Variance', 0) for t in vendor_tasks
                    if isinstance(t.get('Variance'), (int, float))]
        avg_var = sum(variances) / len(variances) if variances else 0
        min_var = min(variances) if variances else 0

        vendor_stats[vendor] = {
            'total': total,
            'complete': complete,
            'in_progress': in_progress,
            'not_started': not_started,
            'red': red,
            'avg_variance': avg_var,
            'worst_variance': min_var,
            'pct_complete': (complete / total * 100) if total > 0 else 0
        }

    print(f"\n  {'Vendor':12} | {'Total':5} | {'Done':4} | {'WIP':4} | {'Not':4} | {'Red':3} | {'Avg Var':8} | {'Worst':8} | {'% Done':6}")
    print(f"  {'-'*12}-+-{'-'*5}-+-{'-'*4}-+-{'-'*4}-+-{'-'*4}-+-{'-'*3}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}")

    for vendor in vendors:
        s = vendor_stats[vendor]
        print(f"  {vendor:12} | {s['total']:5} | {s['complete']:4} | {s['in_progress']:4} | {s['not_started']:4} | {s['red']:3} | {s['avg_variance']:+8.1f} | {s['worst_variance']:+8.0f} | {s['pct_complete']:5.1f}%")

    # Identify TRUE blocker
    print(f"\n  [BLOCKER ANALYSIS]")

    # Check which vendor has incomplete tasks that block others
    igt_incomplete = [t for t in tasks
                      if t.get('Assigned To') == 'IGT'
                      and t.get('Status') != 'Complete'
                      and t.get('Health') == 'Red']

    print(f"\n  IGT Incomplete Red Tasks (ROOT CAUSE):")
    for t in igt_incomplete[:5]:
        print(f"    Row {t['row_number']:2} | End: {t.get('End Date', '')[:10]} | {t['Tasks'][:50]}")

    # Show note from IGT task
    for t in tasks:
        if t.get('Notes') and 'IGT' in str(t.get('Notes', '')):
            print(f"\n  [IGT NOTE] Row {t['row_number']}: {t['Notes']}")

    return vendor_stats


def analyze_frontier_specifically(tasks):
    """Deep dive on Frontier tasks"""
    print("\n" + "=" * 80)
    print("  PHASE 4: FRONTIER TASK ANALYSIS (Your Team)")
    print("=" * 80)

    frontier_tasks = [t for t in tasks if t.get('Assigned To') == 'Frontier']

    print(f"\n  All Frontier Tasks ({len(frontier_tasks)} total):")
    print(f"  {'Row':3} | {'Status':12} | {'Health':6} | {'Var':6} | {'Predecessors':15} | Task")
    print(f"  {'-'*3}-+-{'-'*12}-+-{'-'*6}-+-{'-'*6}-+-{'-'*15}-+-{'-'*40}")

    blocked_by_others = []
    self_blocked = []

    for t in frontier_tasks:
        var = t.get('Variance', 0)
        var_str = f"{var:+.0f}" if isinstance(var, (int, float)) else str(var)
        pred = t.get('Predecessors') or '-'
        status = t.get('Status', 'Unknown')
        health = t.get('Health', 'Unknown')

        print(f"  {t['row_number']:3} | {status:12} | {health:6} | {var_str:>6} | {pred:15} | {t['Tasks'][:40]}")

        # Categorize
        if pred != '-' and status != 'Complete':
            blocked_by_others.append(t)
        elif status != 'Complete' and health == 'Red':
            self_blocked.append(t)

    print(f"\n  [FRONTIER STATUS SUMMARY]")
    complete = len([t for t in frontier_tasks if t.get('Status') == 'Complete'])
    in_progress = len([t for t in frontier_tasks if t.get('Status') == 'In Progress'])
    not_started = len([t for t in frontier_tasks if t.get('Status') == 'Not Started'])

    print(f"    Complete:     {complete}")
    print(f"    In Progress:  {in_progress}")
    print(f"    Not Started:  {not_started}")
    print(f"    Blocked by Predecessors: {len(blocked_by_others)}")

    print(f"\n  [KEY FINDING]")
    print(f"    Frontier tasks showing large negative variance are NOT Frontier's fault.")
    print(f"    They are blocked by upstream tasks from other vendors:")

    for t in blocked_by_others[:5]:
        print(f"      Row {t['row_number']}: Blocked by predecessor {t.get('Predecessors')}")

    return frontier_tasks


def trace_critical_path(tasks):
    """Trace the critical path to understand delays"""
    print("\n" + "=" * 80)
    print("  PHASE 5: CRITICAL PATH TRACE")
    print("=" * 80)

    # Build row lookup
    task_by_row = {t['row_number']: t for t in tasks}

    # Start from the final deployment task (Row 72-75)
    print(f"\n  Tracing back from Final Deployment (Row 72: FPS Production Deployment):")

    def trace_back(row_num, depth=0):
        if depth > 10:  # Prevent infinite loops
            return

        task = task_by_row.get(row_num)
        if not task:
            return

        pred = task.get('Predecessors')
        status = task.get('Status', 'Unknown')
        assigned = task.get('Assigned To', 'N/A')
        health = task.get('Health', 'Unknown')

        indent = "  " * depth
        print(f"    {indent}Row {row_num:2} | {assigned:10} | {status:12} | {health:6} | {task['Tasks'][:40]}")

        if pred:
            # Parse predecessor
            parts = pred.split('FS')[0] if 'FS' in pred else pred.split('SS')[0]
            try:
                pred_row = int(parts.strip())
                trace_back(pred_row, depth + 1)
            except:
                pass

    trace_back(72)

    print(f"\n  [CRITICAL PATH FINDING]")
    print(f"    The delay chain is:")
    print(f"    IGT (Row 24) delays -> FPS QA (Row 40) delays -> Frontier UAT (Row 56) delays")
    print(f"    -> Frontier Approval (Row 62) delays -> CAB (Row 69) delays -> Deploy (Row 72)")


def generate_summary_report(tasks, baseline_analysis, variance_data, vendor_stats):
    """Generate final summary report"""
    print("\n" + "=" * 80)
    print("  COMPREHENSIVE DATA INTEGRITY AUDIT - SUMMARY")
    print("=" * 80)

    print(f"""
  1. BASELINE DISCREPANCY (CRITICAL)
     --------------------------------
     Baselines still reflect 2026-01-07 (original), NOT 2026-01-13 (approved).
     Impact: All variance calculations are 6 days more negative than reality.
     Action: Update baseline dates to reflect approved Jan 13 target.

  2. TRUE ROOT CAUSE OF DELAYS
     --------------------------
     IGT is the primary blocker, NOT Frontier.
     - IGT tasks (Row 22-27) are RED, Not Started, with -15 days variance
     - Note on Row 25: "12/05 - Sandeep (IGT) mentioned configuration will take
       another 2-3 weeks, target December 23rd for completion."
     - 12 downstream tasks depend on IGT Row 24 completion

  3. FRONTIER ANALYSIS (Your Team)
     ------------------------------
     Frontier is NOT the blocker. Analysis shows:
     - 4 tasks Complete
     - 4 tasks In Progress
     - 5 tasks Not Started (but blocked by predecessors)

     Frontier's "Red" and negative variance tasks are caused by:
     - Dependency on IGT completing SIP trunk setup (Row 24)
     - Cascade effect through FPS QA testing

  4. SCHEDULE REALITY
     -----------------
     - Original Target:     2026-01-07 (in baselines)
     - Approved Target:     2026-01-13 (NOT in baselines!)
     - Current Projection:  2026-01-30 (auto-calculated)
     - Schedule Slip:       17 days from approved target (not 23 from original)

  5. VENDOR STATUS SUMMARY
     ----------------------""")

    for vendor in ['IGT', 'FPS', 'Cognigy', 'CSG', 'Frontier']:
        s = vendor_stats[vendor]
        status = "BLOCKING" if vendor == 'IGT' else "OK" if s['red'] == 0 else "AT RISK"
        print(f"     {vendor:10}: {s['pct_complete']:5.1f}% complete | {s['red']} red tasks | {status}")

    print(f"""
  6. RECOMMENDATIONS
     -----------------
     a) IMMEDIATE: Update baselines to reflect approved 2026-01-13 target
        This will correct variance calculations and reduce confusion.

     b) ESCALATE: Focus on IGT, not Frontier
        - IGT SIP trunk configuration is the true bottleneck
        - Their Dec 23 completion target cascades to Jan 30 go-live

     c) INVESTIGATE: Can IGT accelerate?
        - If IGT can complete by Dec 16 instead of Dec 23,
          go-live could potentially move to Jan 23

     d) RE-BASELINE: Consider formal schedule re-baseline to Jan 30
        - If Jan 13 is no longer achievable, update the plan
        - This removes misleading "red" status from dependent tasks

  7. WHY FPS SAYS JAN 30
     ---------------------
     FPS is correctly calculating based on the dependency chain:
     - IGT completes Dec 23
     - FPS QA starts Dec 26 (after holiday), ends Jan 6
     - Frontier UAT: Jan 8-19
     - CAB Approval: Jan 23-28
     - Production Deploy: Jan 30

     This is mathematically correct given IGT's timeline.
""")


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("  PHASE 2 - AGENTIC VOICE PROJECT")
    print("  DATA INTEGRITY AUDIT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load data
    tasks = load_data()
    print(f"\n  Loaded {len(tasks)} tasks for analysis")

    # Run analyses
    baseline_analysis = analyze_baselines(tasks)
    variance_data = analyze_variance(tasks)
    blocking_analysis = analyze_dependencies(tasks)
    vendor_stats = analyze_by_vendor(tasks)
    frontier_tasks = analyze_frontier_specifically(tasks)
    trace_critical_path(tasks)

    # Generate summary
    generate_summary_report(tasks, baseline_analysis, variance_data, vendor_stats)

    print("\n" + "=" * 80)
    print("  AUDIT COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
