"""
Deep Schedule Audit - Phase 2 Agentic Voice Project
Comprehensive analysis of task hierarchy, predecessors, durations, and baselines
Target: Identify ALL issues for cleanup to meet Jan 13, 2026 go-live
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict
import re


def load_data():
    """Load current schedule data"""
    with open('sheet_data_audit.json', 'r') as f:
        return json.load(f)


def parse_date(date_str):
    """Parse date string to datetime"""
    if not date_str:
        return None
    try:
        if 'T' in str(date_str):
            return datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d')
        return datetime.strptime(str(date_str), '%Y-%m-%d')
    except:
        return None


def parse_duration(dur_str):
    """Parse duration string like '3d' to integer days"""
    if not dur_str:
        return None
    match = re.match(r'(\d+)d', str(dur_str))
    if match:
        return int(match.group(1))
    return None


def parse_predecessor(pred_str):
    """Parse predecessor string like '24FS +1d' into components"""
    if not pred_str:
        return None

    # Pattern: row_number + relationship_type + optional_lag
    # Examples: "24FS", "24FS +1d", "5FS", "3FS"
    match = re.match(r'(\d+)(FS|SS|FF|SF)?\s*([+-]\d+d)?', str(pred_str))
    if match:
        return {
            'row': int(match.group(1)),
            'type': match.group(2) or 'FS',  # Default to Finish-to-Start
            'lag': match.group(3) or ''
        }
    return None


def audit_hierarchy(tasks):
    """Audit task hierarchy and groupings"""
    print("\n" + "=" * 80)
    print("  AUDIT 1: TASK HIERARCHY AND GROUPINGS")
    print("=" * 80)

    issues = []

    # Build parent-child relationships
    parents = {}  # row_id -> task
    children = defaultdict(list)  # parent_id -> [child tasks]

    for task in tasks:
        parents[task['row_id']] = task
        if task.get('parent_id'):
            children[task['parent_id']].append(task)

    # Find top-level phases
    phases = [t for t in tasks if t.get('parent_id') is None]
    print(f"\n  Top-Level Phases ({len(phases)}):")
    for phase in phases:
        child_count = len(children.get(phase['row_id'], []))
        print(f"    Row {phase['row_number']:2}: {phase['Tasks']} ({child_count} children)")

    # Check for orphaned tasks (no parent but should have one)
    print(f"\n  Hierarchy Issues:")

    # Check each task's logical grouping
    for task in tasks:
        parent_id = task.get('parent_id')
        task_name = task['Tasks'].lower()
        assigned = task.get('Assigned To', '')

        if parent_id:
            parent = parents.get(parent_id)
            if parent:
                parent_name = parent['Tasks'].lower()
                parent_assigned = parent.get('Assigned To', '')

                # Check if child task vendor matches parent expectation
                if parent_assigned and assigned and parent_assigned != assigned:
                    issues.append({
                        'type': 'VENDOR_MISMATCH',
                        'row': task['row_number'],
                        'task': task['Tasks'],
                        'issue': f"Assigned to {assigned} but parent (Row {parent['row_number']}) is {parent_assigned}",
                        'severity': 'WARN'
                    })

                # Check for misplaced tasks (e.g., QA task under Development)
                if 'qa' in task_name or 'test' in task_name:
                    if 'development' in parent_name and 'qa' not in parent_name:
                        issues.append({
                            'type': 'MISPLACED_TASK',
                            'row': task['row_number'],
                            'task': task['Tasks'],
                            'issue': f"QA/Test task under Development phase (Row {parent['row_number']})",
                            'severity': 'WARN'
                        })

                if 'production' in task_name.lower():
                    if 'staging' in parent_name:
                        issues.append({
                            'type': 'MISPLACED_TASK',
                            'row': task['row_number'],
                            'task': task['Tasks'],
                            'issue': f"Production task under Staging parent (Row {parent['row_number']})",
                            'severity': 'ERROR'
                        })

    # Check for summary tasks without children
    for task in tasks:
        if task.get('parent_id') is None:  # Top-level
            child_list = children.get(task['row_id'], [])
            if len(child_list) == 0 and task['row_number'] > 1:
                issues.append({
                    'type': 'EMPTY_SUMMARY',
                    'row': task['row_number'],
                    'task': task['Tasks'],
                    'issue': 'Summary task has no children',
                    'severity': 'WARN'
                })

    if issues:
        print(f"\n  Found {len(issues)} hierarchy issues:")
        for issue in issues:
            print(f"    [{issue['severity']:5}] Row {issue['row']:2}: {issue['type']}")
            print(f"           {issue['issue']}")
    else:
        print("    No hierarchy issues found")

    return issues


def audit_predecessors(tasks):
    """Audit predecessor relationships"""
    print("\n" + "=" * 80)
    print("  AUDIT 2: PREDECESSOR RELATIONSHIPS")
    print("=" * 80)

    issues = []
    task_by_row = {t['row_number']: t for t in tasks}

    # Count predecessor references
    pred_counts = defaultdict(int)

    for task in tasks:
        pred_str = task.get('Predecessors')
        if pred_str:
            pred = parse_predecessor(pred_str)
            if pred:
                pred_counts[pred['row']] += 1

    print(f"\n  Most Referenced Predecessors (blocking others):")
    for row, count in sorted(pred_counts.items(), key=lambda x: -x[1])[:10]:
        if row in task_by_row:
            t = task_by_row[row]
            status = t.get('Status', 'N/A')
            health = t.get('Health', 'N/A')
            print(f"    Row {row:2}: Blocks {count:2} tasks | {status:12} | {health:6} | {t['Tasks'][:40]}")

    print(f"\n  Predecessor Issues:")

    for task in tasks:
        pred_str = task.get('Predecessors')
        if not pred_str:
            # Check if task should have a predecessor
            if task.get('Status') != 'Complete' and task.get('parent_id'):
                # Non-complete tasks under a parent might need predecessors
                pass  # Not necessarily an issue
            continue

        pred = parse_predecessor(pred_str)
        if not pred:
            issues.append({
                'type': 'INVALID_PREDECESSOR',
                'row': task['row_number'],
                'task': task['Tasks'],
                'issue': f"Cannot parse predecessor: '{pred_str}'",
                'severity': 'ERROR'
            })
            continue

        pred_row = pred['row']

        # Check if predecessor exists
        if pred_row not in task_by_row:
            issues.append({
                'type': 'MISSING_PREDECESSOR',
                'row': task['row_number'],
                'task': task['Tasks'],
                'issue': f"Predecessor Row {pred_row} does not exist",
                'severity': 'ERROR'
            })
            continue

        pred_task = task_by_row[pred_row]

        # Check for self-reference
        if pred_row == task['row_number']:
            issues.append({
                'type': 'SELF_REFERENCE',
                'row': task['row_number'],
                'task': task['Tasks'],
                'issue': 'Task references itself as predecessor',
                'severity': 'ERROR'
            })
            continue

        # Check date logic (successor should start after predecessor ends)
        task_start = parse_date(task.get('Start Date'))
        pred_end = parse_date(pred_task.get('End Date'))

        if task_start and pred_end:
            if pred['type'] == 'FS' and task_start < pred_end:
                # This might be okay with lag, but flag for review
                issues.append({
                    'type': 'DATE_OVERLAP',
                    'row': task['row_number'],
                    'task': task['Tasks'],
                    'issue': f"Starts {task_start.strftime('%Y-%m-%d')} before predecessor Row {pred_row} ends {pred_end.strftime('%Y-%m-%d')}",
                    'severity': 'WARN'
                })

        # Check if predecessor is complete but successor not started
        if pred_task.get('Status') == 'Complete' and task.get('Status') == 'Not Started':
            issues.append({
                'type': 'BLOCKED_BY_COMPLETE',
                'row': task['row_number'],
                'task': task['Tasks'],
                'issue': f"Not started, but predecessor Row {pred_row} is Complete",
                'severity': 'INFO'
            })

        # Check vendor dependency logic
        task_vendor = task.get('Assigned To')
        pred_vendor = pred_task.get('Assigned To')

        if task_vendor and pred_vendor and task_vendor != pred_vendor:
            # Cross-vendor dependency - flag for review
            pass  # This is normal, not an issue

    # Check for potential missing predecessors
    print(f"\n  Tasks Without Predecessors (potential issues):")
    no_pred_issues = []
    for task in tasks:
        if not task.get('Predecessors') and task.get('parent_id'):
            status = task.get('Status', '')
            if status not in ['Complete', 'In Progress']:
                # Check if siblings have predecessors
                parent_id = task.get('parent_id')
                siblings = [t for t in tasks if t.get('parent_id') == parent_id]
                siblings_with_pred = [s for s in siblings if s.get('Predecessors')]

                if len(siblings_with_pred) > 0 and len(siblings_with_pred) < len(siblings):
                    no_pred_issues.append({
                        'type': 'MISSING_PREDECESSOR',
                        'row': task['row_number'],
                        'task': task['Tasks'],
                        'issue': f"No predecessor but {len(siblings_with_pred)}/{len(siblings)} siblings have predecessors",
                        'severity': 'WARN'
                    })

    issues.extend(no_pred_issues)

    if issues:
        print(f"\n  Found {len(issues)} predecessor issues:")
        for issue in sorted(issues, key=lambda x: (x['severity'], x['row'])):
            print(f"    [{issue['severity']:5}] Row {issue['row']:2}: {issue['type']}")
            print(f"           {issue['issue']}")

    return issues


def audit_durations(tasks):
    """Audit durations vs actual date spans"""
    print("\n" + "=" * 80)
    print("  AUDIT 3: DURATION VALIDATION")
    print("=" * 80)

    issues = []

    print(f"\n  Duration Mismatches:")

    for task in tasks:
        dur_str = task.get('Duration')
        start = parse_date(task.get('Start Date'))
        end = parse_date(task.get('End Date'))

        if not dur_str or not start or not end:
            continue

        stated_dur = parse_duration(dur_str)
        if stated_dur is None:
            continue

        # Calculate actual calendar days
        actual_days = (end - start).days + 1  # Inclusive

        # Calculate business days (rough estimate, excluding weekends)
        business_days = 0
        current = start
        while current <= end:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                business_days += 1
            current += timedelta(days=1)

        # Check for significant mismatches
        # Smartsheet durations are typically business days
        if abs(stated_dur - business_days) > 2:
            issues.append({
                'type': 'DURATION_MISMATCH',
                'row': task['row_number'],
                'task': task['Tasks'],
                'stated': stated_dur,
                'actual_cal': actual_days,
                'actual_biz': business_days,
                'issue': f"Stated {stated_dur}d but spans {actual_days} calendar days ({business_days} business days)",
                'severity': 'WARN'
            })

    if issues:
        print(f"\n  Found {len(issues)} duration issues:")
        for issue in issues[:15]:  # Show first 15
            print(f"    Row {issue['row']:2}: {issue['task'][:40]}")
            print(f"           Stated: {issue['stated']}d | Calendar: {issue['actual_cal']}d | Business: {issue['actual_biz']}d")
        if len(issues) > 15:
            print(f"    ... and {len(issues) - 15} more")
    else:
        print("    No significant duration mismatches found")

    return issues


def audit_baselines(tasks):
    """Audit baselines and calculate correct values for Jan 13 target"""
    print("\n" + "=" * 80)
    print("  AUDIT 4: BASELINE ANALYSIS FOR JAN 13, 2026 TARGET")
    print("=" * 80)

    target_date = datetime(2026, 1, 13)
    original_baseline = datetime(2026, 1, 7)

    issues = []
    recommendations = []

    print(f"\n  Target Go-Live: {target_date.strftime('%Y-%m-%d')}")
    print(f"  Original Baseline: {original_baseline.strftime('%Y-%m-%d')}")
    print(f"  Baseline Shift Needed: +6 days")

    # Analyze current baselines
    baseline_stats = {
        'at_original': [],
        'before_original': [],
        'after_original': [],
        'missing': []
    }

    for task in tasks:
        bf = parse_date(task.get('Baseline Finish'))
        if not bf:
            baseline_stats['missing'].append(task)
            continue

        if bf == original_baseline:
            baseline_stats['at_original'].append(task)
        elif bf < original_baseline:
            baseline_stats['before_original'].append(task)
        else:
            baseline_stats['after_original'].append(task)

    print(f"\n  Current Baseline Distribution:")
    print(f"    At Jan 7 (original):     {len(baseline_stats['at_original'])} tasks")
    print(f"    Before Jan 7:            {len(baseline_stats['before_original'])} tasks")
    print(f"    After Jan 7:             {len(baseline_stats['after_original'])} tasks (should not exist)")
    print(f"    Missing baseline:        {len(baseline_stats['missing'])} tasks")

    # Tasks ending on baseline need adjustment
    print(f"\n  Tasks Requiring Baseline Update to Jan 13:")
    for task in baseline_stats['at_original']:
        print(f"    Row {task['row_number']:2}: {task['Tasks'][:50]}")
        recommendations.append({
            'row': task['row_number'],
            'task': task['Tasks'],
            'current_baseline': '2026-01-07',
            'new_baseline': '2026-01-13',
            'action': 'UPDATE_BASELINE'
        })

    # Calculate what end dates should be
    print(f"\n  End Date Analysis (Current vs Target):")

    end_date_issues = []
    for task in tasks:
        end = parse_date(task.get('End Date'))
        bf = parse_date(task.get('Baseline Finish'))

        if end and end > target_date:
            days_over = (end - target_date).days
            end_date_issues.append({
                'row': task['row_number'],
                'task': task['Tasks'],
                'end_date': end.strftime('%Y-%m-%d'),
                'days_over': days_over,
                'assigned': task.get('Assigned To', 'N/A')
            })

    if end_date_issues:
        print(f"\n  Tasks Ending AFTER Jan 13 Target ({len(end_date_issues)}):")
        end_date_issues.sort(key=lambda x: -x['days_over'])
        for issue in end_date_issues[:20]:
            assigned = issue['assigned'] or 'N/A'
            print(f"    Row {issue['row']:2} | +{issue['days_over']:2}d | {assigned:10} | {issue['task'][:40]}")

        print(f"\n  [CRITICAL] To meet Jan 13, these {len(end_date_issues)} tasks need schedule compression")

    return issues, recommendations, end_date_issues


def audit_logical_sequence(tasks):
    """Audit logical sequence of tasks"""
    print("\n" + "=" * 80)
    print("  AUDIT 5: LOGICAL SEQUENCE ANALYSIS")
    print("=" * 80)

    issues = []

    # Define expected phase sequence
    expected_phases = [
        'development',
        'qa', 'testing', 'test',
        'uat',
        'production', 'deployment'
    ]

    # Check if tasks follow logical sequence
    print(f"\n  Task Sequence Issues:")

    for task in tasks:
        task_name = task['Tasks'].lower()
        end = parse_date(task.get('End Date'))

        # Find other related tasks
        for other in tasks:
            if other['row_number'] == task['row_number']:
                continue

            other_name = other['Tasks'].lower()
            other_end = parse_date(other.get('End Date'))

            if not end or not other_end:
                continue

            # Check for sequence violations
            # UAT should come after QA
            if 'uat' in task_name and 'qa' in other_name and 'uat' not in other_name:
                if end < other_end:
                    issues.append({
                        'type': 'SEQUENCE_VIOLATION',
                        'row': task['row_number'],
                        'task': task['Tasks'],
                        'issue': f"UAT (Row {task['row_number']}) ends before QA (Row {other['row_number']})",
                        'severity': 'ERROR'
                    })

            # Production should come after UAT
            if 'production deploy' in task_name and 'uat' in other_name:
                if end < other_end:
                    issues.append({
                        'type': 'SEQUENCE_VIOLATION',
                        'row': task['row_number'],
                        'task': task['Tasks'],
                        'issue': f"Production Deploy ends before UAT (Row {other['row_number']})",
                        'severity': 'ERROR'
                    })

    # Remove duplicates
    seen = set()
    unique_issues = []
    for issue in issues:
        key = (issue['row'], issue['type'])
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    if unique_issues:
        print(f"\n  Found {len(unique_issues)} sequence issues:")
        for issue in unique_issues[:10]:
            print(f"    [{issue['severity']:5}] {issue['issue']}")
    else:
        print("    No sequence issues found")

    return unique_issues


def calculate_critical_path(tasks):
    """Calculate the critical path to Jan 13"""
    print("\n" + "=" * 80)
    print("  AUDIT 6: CRITICAL PATH TO JAN 13, 2026")
    print("=" * 80)

    target = datetime(2026, 1, 13)
    today = datetime(2025, 12, 9)

    days_remaining = (target - today).days
    print(f"\n  Days Remaining to Target: {days_remaining} days")

    # Find tasks on critical path (those that must complete for go-live)
    task_by_row = {t['row_number']: t for t in tasks}

    # Start from final deployment and trace back
    final_tasks = [t for t in tasks if 'production deployment' in t['Tasks'].lower()
                   or 'fps production' in t['Tasks'].lower()]

    print(f"\n  Final Deployment Tasks:")
    for t in final_tasks:
        end = parse_date(t.get('End Date'))
        end_str = end.strftime('%Y-%m-%d') if end else 'N/A'
        variance = (end - target).days if end else 0
        print(f"    Row {t['row_number']:2}: {t['Tasks'][:40]}")
        print(f"           End: {end_str} | Days from target: {variance:+d}")

    # Trace critical path backwards
    print(f"\n  Critical Path (tracing backwards from deployment):")

    def trace_path(row_num, depth=0, visited=None):
        if visited is None:
            visited = set()
        if row_num in visited or depth > 15:
            return []
        visited.add(row_num)

        task = task_by_row.get(row_num)
        if not task:
            return []

        path = [task]

        pred_str = task.get('Predecessors')
        if pred_str:
            pred = parse_predecessor(pred_str)
            if pred:
                path.extend(trace_path(pred['row'], depth + 1, visited))

        return path

    # Get critical path from row 72 (FPS Production Deployment)
    critical_path = trace_path(72)

    if critical_path:
        print(f"\n  Critical Path ({len(critical_path)} tasks):")
        for i, task in enumerate(critical_path):
            indent = "  " * i
            end = parse_date(task.get('End Date'))
            end_str = end.strftime('%m/%d') if end else 'N/A'
            status = task.get('Status', 'N/A')[:8]
            assigned = task.get('Assigned To', 'N/A') or 'N/A'
            print(f"    {indent}Row {task['row_number']:2} | {end_str} | {status:8} | {assigned:10} | {task['Tasks'][:35]}")

    # Calculate required compression
    current_end = parse_date(tasks[0].get('End Date'))  # Development phase
    for t in tasks:
        end = parse_date(t.get('End Date'))
        if end and (not current_end or end > current_end):
            current_end = end

    if current_end:
        compression_needed = (current_end - target).days
        print(f"\n  [SCHEDULE COMPRESSION NEEDED]")
        print(f"    Current End:      {current_end.strftime('%Y-%m-%d')}")
        print(f"    Target:           {target.strftime('%Y-%m-%d')}")
        print(f"    Days to Compress: {compression_needed} days")

    return critical_path


def generate_correction_plan(tasks, all_issues):
    """Generate detailed correction plan"""
    print("\n" + "=" * 80)
    print("  COMPREHENSIVE CORRECTION PLAN")
    print("=" * 80)

    # Group issues by type
    by_type = defaultdict(list)
    for issue_list in all_issues:
        if isinstance(issue_list, list):
            for issue in issue_list:
                if isinstance(issue, dict) and 'type' in issue:
                    by_type[issue['type']].append(issue)

    print(f"""
  PHASE 1: BASELINE UPDATES (Immediate)
  ======================================
  Update baseline finish dates from Jan 7 to Jan 13 for:
  - All tasks currently baselined at 2026-01-07
  - This shifts variance calculations by +6 days

  Smartsheet Steps:
  1. Select all rows
  2. Project Settings > Baselines > Re-baseline
  3. Or manually update Baseline Finish column

  PHASE 2: PREDECESSOR CLEANUP (High Priority)
  =============================================
  Focus on Row 24 (IGT SIP Trunks) - blocks 20 tasks

  Questions to resolve:
  1. Can any blocked tasks start in parallel?
  2. Should dependencies be on Row 22 (parent) instead?
  3. Are all 20 dependencies truly sequential?

  Rows to review:
""")

    # List rows with predecessor issues
    pred_issues = by_type.get('DATE_OVERLAP', []) + by_type.get('BLOCKED_BY_COMPLETE', [])
    for issue in pred_issues[:10]:
        print(f"    Row {issue['row']:2}: {issue['issue'][:60]}")

    print(f"""
  PHASE 3: DURATION ADJUSTMENTS (Medium Priority)
  ================================================
  Several tasks have duration/date mismatches.
  Review and correct:
""")

    dur_issues = by_type.get('DURATION_MISMATCH', [])
    for issue in dur_issues[:5]:
        print(f"    Row {issue['row']:2}: {issue.get('issue', 'Duration mismatch')[:60]}")

    print(f"""
  PHASE 4: HIERARCHY CLEANUP (Low Priority)
  ==========================================
  Tasks that may be misplaced:
""")

    hier_issues = by_type.get('MISPLACED_TASK', []) + by_type.get('VENDOR_MISMATCH', [])
    for issue in hier_issues[:5]:
        print(f"    Row {issue['row']:2}: {issue['issue'][:60]}")

    print(f"""
  PHASE 5: SCHEDULE COMPRESSION (Critical)
  =========================================
  To meet Jan 13 target, need to compress by 17 days.

  Options:
  1. ACCELERATE IGT: Can they complete by Dec 16 instead of Dec 23?
     - Saves 7 days
     - Cascades through entire schedule

  2. PARALLELIZE: Identify tasks that can run concurrently
     - FPS QA and some Cognigy tasks
     - Review all "24FS +1d" dependencies

  3. COMPRESS UAT: Reduce Frontier UAT from 8 days to 5 days
     - Saves 3 days
     - Requires agreement with Frontier

  4. COMPRESS CAB: Reduce approval window from 4 days to 2 days
     - Saves 2 days
     - Requires process change

  TOTAL POTENTIAL SAVINGS: ~12-15 days
  GAP TO TARGET: Still 2-5 days short

  RECOMMENDATION:
  If Jan 13 is firm, escalate IGT dependency immediately.
  If Jan 13 is flexible, re-baseline to Jan 20-23 as compromise.
""")


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("  DEEP SCHEDULE AUDIT - PHASE 2 AGENTIC VOICE")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Target: Identify ALL issues for Jan 13, 2026 go-live")
    print("=" * 80)

    tasks = load_data()
    print(f"\n  Analyzing {len(tasks)} tasks...")

    all_issues = []

    # Run all audits
    hierarchy_issues = audit_hierarchy(tasks)
    all_issues.append(hierarchy_issues)

    predecessor_issues = audit_predecessors(tasks)
    all_issues.append(predecessor_issues)

    duration_issues = audit_durations(tasks)
    all_issues.append(duration_issues)

    baseline_issues, recommendations, end_date_issues = audit_baselines(tasks)
    all_issues.append(baseline_issues)

    sequence_issues = audit_logical_sequence(tasks)
    all_issues.append(sequence_issues)

    critical_path = calculate_critical_path(tasks)

    # Generate correction plan
    generate_correction_plan(tasks, all_issues)

    # Summary
    total_issues = sum(len(i) for i in all_issues if isinstance(i, list))

    print("\n" + "=" * 80)
    print(f"  AUDIT SUMMARY")
    print("=" * 80)
    print(f"  Total Issues Found: {total_issues}")
    print(f"  Tasks Over Target:  {len(end_date_issues)}")
    print(f"  Critical Path Length: {len(critical_path)} tasks")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
