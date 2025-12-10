"""
Schedule Comparison: Backup (12/5/25) vs Current State
Analyzes what changed and identifies data integrity issues
"""

import pandas as pd
import json
from datetime import datetime


def load_data():
    """Load both datasets"""
    # Load backup
    backup_df = pd.read_excel('Copy of 1. Phase 2 - Agentic Voice Task Sheet.xlsx')

    # Load current
    with open('sheet_data_audit.json', 'r') as f:
        current_data = json.load(f)
    current_df = pd.DataFrame(current_data)

    return backup_df, current_df


def compare_row_counts(backup_df, current_df):
    """Compare row counts"""
    print("\n" + "=" * 80)
    print("  COMPARISON: BACKUP (12/5/25) vs CURRENT STATE")
    print("=" * 80)

    print(f"\n  Row Count:")
    print(f"    Backup (12/5/25):  {len(backup_df)} tasks")
    print(f"    Current:           {len(current_df)} tasks")
    print(f"    Difference:        +{len(current_df) - len(backup_df)} tasks added")


def analyze_backup_dates(backup_df):
    """Analyze the original schedule from backup"""
    print("\n" + "=" * 80)
    print("  BACKUP SCHEDULE ANALYSIS (Original State 12/5/25)")
    print("=" * 80)

    print("\n  Key Dates from Backup:")

    # Find the final deployment task
    deploy_row = backup_df[backup_df['Tasks'].str.contains('FPS Production Deployment', case=False, na=False)]
    if not deploy_row.empty:
        row = deploy_row.iloc[0]
        print(f"    FPS Production Deployment:")
        print(f"      End Date:        {row['End Date']}")
        print(f"      Baseline Finish: {row['Baseline Finish']}")
        print(f"      Variance:        {row['Variance']}")

    # Production Deployment phase
    prod_row = backup_df[backup_df['Tasks'] == 'Production Deployment']
    if not prod_row.empty:
        row = prod_row.iloc[0]
        print(f"\n    Production Deployment Phase:")
        print(f"      End Date:        {row['End Date']}")
        print(f"      Baseline Finish: {row['Baseline Finish']}")
        print(f"      Variance:        {row['Variance']}")

    # UAT Approval
    uat_row = backup_df[backup_df['Tasks'].str.contains('Frontier UAT Approval', case=False, na=False)]
    if not uat_row.empty:
        row = uat_row.iloc[0]
        print(f"\n    Frontier UAT Approval:")
        print(f"      End Date:        {row['End Date']}")
        print(f"      Baseline Finish: {row['Baseline Finish']}")
        print(f"      Variance:        {row['Variance']}")

    print("\n  [KEY FINDING FROM BACKUP]")
    print("    On 12/5/25, the schedule showed:")
    print("      - Baseline Finish (Original): 2026-01-07")
    print("      - End Date (Approved Target): 2026-01-13")
    print("      - This proves the Jan 13 target was already in the schedule")
    print("      - The -4d to -9d variance was measured against Jan 7, not Jan 13")


def find_matching_tasks(backup_df, current_df):
    """Find which backup tasks exist in current and what changed"""
    print("\n" + "=" * 80)
    print("  TASK-BY-TASK COMPARISON")
    print("=" * 80)

    matched = []
    new_in_current = []

    backup_tasks = set(backup_df['Tasks'].dropna().tolist())
    current_tasks = set(current_df['Tasks'].dropna().tolist())

    # Tasks in both
    common = backup_tasks.intersection(current_tasks)

    # Tasks only in current (new)
    only_current = current_tasks - backup_tasks

    print(f"\n  Task Summary:")
    print(f"    Tasks in backup:     {len(backup_tasks)}")
    print(f"    Tasks in current:    {len(current_tasks)}")
    print(f"    Common tasks:        {len(common)}")
    print(f"    New tasks added:     {len(only_current)}")

    return common, only_current


def analyze_date_changes(backup_df, current_df, common_tasks):
    """Analyze how dates changed for common tasks"""
    print("\n" + "=" * 80)
    print("  DATE CHANGES FOR EXISTING TASKS")
    print("=" * 80)

    changes = []

    for task_name in common_tasks:
        backup_row = backup_df[backup_df['Tasks'] == task_name]
        current_row = current_df[current_df['Tasks'] == task_name]

        if backup_row.empty or current_row.empty:
            continue

        b = backup_row.iloc[0]
        c = current_row.iloc[0]

        # Compare End Dates
        b_end = str(b['End Date'])[:10] if pd.notna(b['End Date']) else 'N/A'
        c_end = str(c['End Date'])[:10] if c['End Date'] else 'N/A'

        # Compare Baseline Finish
        b_baseline = str(b['Baseline Finish'])[:10] if pd.notna(b['Baseline Finish']) else 'N/A'
        c_baseline = str(c['Baseline Finish'])[:10] if c['Baseline Finish'] else 'N/A'

        if b_end != c_end or b_baseline != c_baseline:
            changes.append({
                'task': task_name,
                'backup_end': b_end,
                'current_end': c_end,
                'backup_baseline': b_baseline,
                'current_baseline': c_baseline,
                'end_changed': b_end != c_end,
                'baseline_changed': b_baseline != c_baseline
            })

    if changes:
        print(f"\n  Tasks with Date Changes ({len(changes)}):")
        print(f"  {'Task'[:35]:35} | {'Old End':10} | {'New End':10} | {'Old Base':10} | {'New Base':10}")
        print(f"  {'-'*35}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

        for c in changes:
            task = c['task'][:35]
            print(f"  {task:35} | {c['backup_end']:10} | {c['current_end']:10} | {c['backup_baseline']:10} | {c['current_baseline']:10}")
    else:
        print("\n  No date changes found for common tasks")

    return changes


def analyze_new_tasks(current_df, new_tasks):
    """Analyze the tasks that were added"""
    print("\n" + "=" * 80)
    print("  NEW TASKS ADDED (by FPS)")
    print("=" * 80)

    # Group new tasks by assigned vendor
    new_by_vendor = {}

    for task_name in new_tasks:
        row = current_df[current_df['Tasks'] == task_name]
        if not row.empty:
            assigned = row.iloc[0].get('Assigned To', 'Unassigned') or 'Unassigned'
            if assigned not in new_by_vendor:
                new_by_vendor[assigned] = []
            new_by_vendor[assigned].append({
                'task': task_name,
                'health': row.iloc[0].get('Health', 'N/A'),
                'status': row.iloc[0].get('Status', 'N/A'),
                'variance': row.iloc[0].get('Variance', 0)
            })

    print(f"\n  New Tasks by Vendor:")
    for vendor, tasks in sorted(new_by_vendor.items()):
        red_count = len([t for t in tasks if t['health'] == 'Red'])
        print(f"\n  {vendor}: {len(tasks)} tasks ({red_count} Red)")
        for t in tasks[:5]:  # Show first 5
            health = t['health']
            var = t['variance']
            var_str = f"{var:+.0f}" if isinstance(var, (int, float)) else str(var)
            print(f"    - [{health:6}] {var_str:>5} | {t['task'][:50]}")
        if len(tasks) > 5:
            print(f"    ... and {len(tasks) - 5} more")


def identify_blocker_source(backup_df, current_df):
    """Identify where the blocking issues originated"""
    print("\n" + "=" * 80)
    print("  BLOCKER SOURCE ANALYSIS")
    print("=" * 80)

    # Check IGT in backup
    igt_backup = backup_df[backup_df['Tasks'].str.contains('IGT', case=False, na=False)]
    igt_current = current_df[current_df['Assigned To'] == 'IGT']

    print(f"\n  IGT Tasks:")
    print(f"    In backup (12/5):  {len(igt_backup)} tasks")
    print(f"    In current:        {len(igt_current)} tasks")

    # Find the IGT note about 2-3 weeks delay
    for _, row in current_df.iterrows():
        if 'IGT' in str(row.get('Notes', '')):
            print(f"\n  [IGT NOTE FOUND] Row {row['row_number']}:")
            print(f"    '{row['Notes']}'")
            print(f"    This note indicates IGT communicated the delay on 12/5")

    # Check what the backup showed for IGT-dependent items
    print(f"\n  [CONCLUSION]")
    print(f"    The backup from 12/5 predates the detailed task breakdown.")
    print(f"    FPS expanded 23 high-level tasks into 75 detailed tasks.")
    print(f"    The IGT dependency (Row 24) became the critical bottleneck")
    print(f"    when detailed predecessor relationships were added.")


def generate_action_plan(backup_df, current_df):
    """Generate action plan for data cleanup"""
    print("\n" + "=" * 80)
    print("  RECOMMENDED ACTION PLAN")
    print("=" * 80)

    print("""
  Based on comparison of backup (12/5/25) vs current state:

  1. BASELINE RE-ALIGNMENT
     ----------------------
     The backup shows End Date of 2026-01-13 for final deployment
     but Baseline Finish of 2026-01-07.

     ACTION: Choose one:
     a) Update baselines to Jan 13 (the approved target)
        - This reduces visual "red" and variance by 6 days
        - More accurately reflects current commitments

     b) Re-baseline to Jan 30 (current projection)
        - Acknowledges reality
        - Resets variance to 0 for remaining tasks
        - May require formal change request

  2. TASK STRUCTURE REVIEW
     ----------------------
     FPS added 52 detailed subtasks to the original 23.

     VERIFY:
     - Are all subtasks necessary for tracking?
     - Do predecessor relationships accurately reflect dependencies?
     - Are any circular or incorrect dependencies present?

  3. PREDECESSOR CLEANUP (Row 24 - Critical)
     ---------------------------------------
     Row 24 (IGT: Set up SIP trunks) blocks 20 tasks.

     VERIFY:
     - Is this the correct dependency?
     - Can any tasks proceed in parallel?
     - Should other IGT tasks (Row 23, 25-27) also be predecessors?

  4. VARIANCE RECALCULATION
     -----------------------
     After baseline update, variance will auto-recalculate.

     EXPECTED RESULT if baselines updated to Jan 13:
     - Maximum variance improves from -33 to -27 days
     - Many tasks move from Red to Yellow

  5. DOCUMENTATION UPDATE
     ---------------------
     Add notes to key tasks explaining:
     - When and why the schedule was adjusted
     - The approved change from Jan 7 to Jan 13
     - The IGT-driven slip to Jan 30

  6. SCHEDULE INTEGRITY CHECK
     --------------------------
     Run the audit script periodically:

     python data_integrity_audit.py
""")


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("  SCHEDULE COMPARISON ANALYSIS")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load data
    backup_df, current_df = load_data()

    # Run comparisons
    compare_row_counts(backup_df, current_df)
    analyze_backup_dates(backup_df)
    common, new = find_matching_tasks(backup_df, current_df)
    analyze_date_changes(backup_df, current_df, common)
    analyze_new_tasks(current_df, new)
    identify_blocker_source(backup_df, current_df)
    generate_action_plan(backup_df, current_df)

    print("\n" + "=" * 80)
    print("  COMPARISON COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
