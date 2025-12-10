"""
Schedule Correction for Jan 13, 2026 Target
Accounts for:
1. FPS developer pulled off Nov 25 - Dec 9 (4 working day shift agreed)
2. IGT SIP Trunks taking 2-3 weeks (Dec 8 -> Dec 23)

This script generates the corrected schedule and Smartsheet update payload.
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict

# Constants
TARGET_GO_LIVE = datetime(2026, 1, 13)
ORIGINAL_BASELINE = datetime(2026, 1, 7)
BASELINE_SHIFT = 6  # Days from Jan 7 to Jan 13

# IGT completion date (per 12/05 note: 2-3 more weeks from Dec 8)
IGT_STAGING_COMPLETE = datetime(2025, 12, 23)

# Holidays to skip
HOLIDAYS = [
    datetime(2025, 12, 24),  # Christmas Eve
    datetime(2025, 12, 25),  # Christmas Day
    datetime(2025, 12, 26),  # Day after Christmas
    datetime(2026, 1, 1),    # New Year's Day
]


def load_schedule():
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


def add_work_days(start_date, days):
    """Add working days, skipping weekends and holidays"""
    current = start_date
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        # Skip weekends
        if current.weekday() >= 5:
            continue
        # Skip holidays
        if current in HOLIDAYS:
            continue
        remaining -= 1
    return current


def parse_duration(dur_str):
    """Parse duration string like '5d' to integer days"""
    if not dur_str:
        return 1
    try:
        return int(str(dur_str).replace('d', ''))
    except:
        return 1


def parse_predecessor(pred_str):
    """Parse predecessor string like '24FS +1d' into components"""
    if not pred_str:
        return None

    import re
    # Match patterns like "24FS", "24FS +1d", "24SS", etc.
    match = re.match(r'(\d+)(FS|SS|FF|SF)?\s*([+-]\d+d)?', pred_str.strip())
    if match:
        row = int(match.group(1))
        link_type = match.group(2) or 'FS'
        lag = 0
        if match.group(3):
            lag = int(match.group(3).replace('d', '').replace('+', ''))
        return {'row': row, 'type': link_type, 'lag': lag}
    return None


def calculate_corrected_schedule(tasks):
    """Calculate the corrected schedule based on Jan 13 target and IGT completion"""

    # Build task lookup by row
    task_by_row = {t['row_number']: t for t in tasks}

    corrections = []

    # Process each task
    for task in tasks:
        row = task['row_number']
        name = task['Tasks']
        assigned = task.get('Assigned To', '')
        status = task.get('Status', '')

        current_end = parse_date(task.get('End Date'))
        current_start = parse_date(task.get('Start Date'))
        current_baseline_finish = parse_date(task.get('Baseline Finish'))
        current_baseline_start = parse_date(task.get('Baseline Start'))
        duration = parse_duration(task.get('Duration'))
        pred_str = task.get('Predecessors')

        correction = {
            'row_number': row,
            'row_id': task['row_id'],
            'task_name': name,
            'assigned_to': assigned,
            'status': status,
            'current_end': current_end,
            'current_start': current_start,
            'current_baseline_finish': current_baseline_finish,
            'current_baseline_start': current_baseline_start,
            'duration': duration,
            'predecessor': pred_str,

            # Corrections to apply
            'new_baseline_finish': None,
            'new_baseline_start': None,
            'new_end_date': None,
            'new_start_date': None,
            'baseline_action': '',
            'schedule_action': '',
            'notes': ''
        }

        # Skip completed tasks - no baseline change needed
        if status == 'Complete':
            correction['baseline_action'] = 'KEEP (Complete)'
            correction['notes'] = 'Task already complete - no changes needed'
            corrections.append(correction)
            continue

        # Calculate new baseline based on task type
        if current_baseline_finish:
            baseline_delta = (ORIGINAL_BASELINE - current_baseline_finish).days

            if baseline_delta == 0:
                # Task was at Jan 7 baseline - shift to Jan 13
                correction['new_baseline_finish'] = TARGET_GO_LIVE
                correction['baseline_action'] = 'SHIFT +6d (Jan 7 -> Jan 13)'
                if current_baseline_start:
                    correction['new_baseline_start'] = current_baseline_start + timedelta(days=BASELINE_SHIFT)

            elif baseline_delta > 0:
                # Task was before Jan 7 - proportionally shift
                new_baseline = TARGET_GO_LIVE - timedelta(days=baseline_delta)
                correction['new_baseline_finish'] = new_baseline
                correction['baseline_action'] = f'PROPORTIONAL SHIFT ({baseline_delta}d before target)'
                if current_baseline_start:
                    correction['new_baseline_start'] = current_baseline_start + timedelta(days=BASELINE_SHIFT)

            else:
                # Task was after Jan 7 - should not happen for baseline
                correction['baseline_action'] = 'REVIEW - baseline after original target'

        # Check if task depends on IGT Row 24 (the SIP trunks blocker)
        if pred_str and '24' in pred_str:
            pred = parse_predecessor(pred_str)
            if pred and pred['row'] == 24:
                # This task depends on IGT - recalculate from Dec 23
                new_start = add_work_days(IGT_STAGING_COMPLETE, pred.get('lag', 0))
                new_end = add_work_days(new_start, duration - 1) if duration > 1 else new_start

                correction['new_start_date'] = new_start
                correction['new_end_date'] = new_end
                correction['schedule_action'] = f'RECALC from IGT Dec 23 + {pred.get("lag", 0)}d'
                correction['notes'] = 'Blocked by IGT Row 24 (SIP Trunks)'

        # Check if task depends on another task that depends on Row 24
        elif pred_str:
            pred = parse_predecessor(pred_str)
            if pred:
                pred_task = task_by_row.get(pred['row'])
                if pred_task:
                    pred_pred = pred_task.get('Predecessors', '')
                    if '24' in str(pred_pred):
                        # Indirect dependency on IGT
                        correction['notes'] = f"Indirect IGT dependency via Row {pred['row']}"

        corrections.append(correction)

    return corrections


def generate_smartsheet_updates(corrections):
    """Generate the Smartsheet API update payload"""

    updates = []

    for corr in corrections:
        if corr['status'] == 'Complete':
            continue

        row_update = {
            'id': corr['row_id'],
            'cells': []
        }

        # Baseline Finish update
        if corr['new_baseline_finish']:
            row_update['cells'].append({
                'columnId': 'BASELINE_FINISH_COLUMN_ID',  # Will need actual column ID
                'value': corr['new_baseline_finish'].strftime('%Y-%m-%d'),
                'field': 'Baseline Finish'
            })

        # Baseline Start update
        if corr['new_baseline_start']:
            row_update['cells'].append({
                'columnId': 'BASELINE_START_COLUMN_ID',  # Will need actual column ID
                'value': corr['new_baseline_start'].strftime('%Y-%m-%d'),
                'field': 'Baseline Start'
            })

        if row_update['cells']:
            updates.append(row_update)

    return updates


def calculate_critical_path_dates():
    """Calculate the critical path dates based on IGT completion and SOW durations"""

    print("\n" + "=" * 90)
    print("  CRITICAL PATH RECALCULATION")
    print("  Based on: IGT SIP Trunks complete Dec 23, FPS dev resumes Dec 9")
    print("=" * 90)

    # Key milestones from SOW with original durations
    sow_durations = {
        'IGT Staging Dependencies': (datetime(2025, 12, 8), datetime(2025, 12, 8), 1),  # Was 1d, now 12d
        'Cognigy Staging Phase 2': (datetime(2025, 12, 8), datetime(2025, 12, 8), 1),
        'FPS QA Testing': (datetime(2025, 12, 8), datetime(2025, 12, 12), 5),  # Dec 8-12 = 5d
        'Cognigy Production Dependencies': (datetime(2025, 12, 15), datetime(2025, 12, 15), 1),
        'IGT Production Dependencies': (datetime(2025, 12, 15), datetime(2025, 12, 15), 1),
        'Frontier UAT Testing': (datetime(2025, 12, 15), datetime(2025, 12, 19), 5),  # Dec 15-19 = 5d
        'Frontier UAT Approval': (datetime(2025, 12, 19), datetime(2025, 12, 19), 1),
        'Frontier Production Keys': (datetime(2026, 1, 5), datetime(2026, 1, 5), 1),
        'CAB Approval': (datetime(2026, 1, 6), datetime(2026, 1, 6), 1),
        'Production Deployment': (datetime(2026, 1, 7), datetime(2026, 1, 14), 5),  # Jan 7-14
    }

    # Calculate forward from IGT completion (Dec 23)
    print("\n  Forward Pass from IGT Completion (Dec 23):")
    print(f"  {'Milestone':<40} | {'SOW':^12} | {'Recalc':^12} | {'Delta':^8}")
    print(f"  {'-'*40}-+-{'-'*12}-+-{'-'*12}-+-{'-'*8}")

    # IGT Staging complete Dec 23
    igt_complete = datetime(2025, 12, 23)
    print(f"  {'IGT Staging Complete':<40} | {'Dec 08':^12} | {'Dec 23':^12} | {'+15d':^8}")

    # Cognigy Staging Phase 2 - starts after IGT + 1d
    cognigy_staging_start = add_work_days(igt_complete, 1)
    cognigy_staging_end = add_work_days(cognigy_staging_start, 2)  # 3d duration
    print(f"  {'Cognigy Staging Phase 2':<40} | {'Dec 08':^12} | {cognigy_staging_end.strftime('%b %d'):^12} | {'+' + str((cognigy_staging_end - datetime(2025, 12, 8)).days) + 'd':^8}")

    # FPS QA Testing - starts after IGT + 1d, 5 working days
    fps_qa_start = add_work_days(igt_complete, 1)
    fps_qa_end = add_work_days(fps_qa_start, 4)  # 5d including start
    print(f"  {'FPS QA Testing':<40} | {'Dec 12':^12} | {fps_qa_end.strftime('%b %d'):^12} | {'+' + str((fps_qa_end - datetime(2025, 12, 12)).days) + 'd':^8}")

    # Frontier UAT - starts after FPS QA + 1d, 5 working days
    frontier_uat_start = add_work_days(fps_qa_end, 1)
    frontier_uat_end = add_work_days(frontier_uat_start, 4)  # 5d including start
    print(f"  {'Frontier UAT Testing':<40} | {'Dec 19':^12} | {frontier_uat_end.strftime('%b %d'):^12} | {'+' + str((frontier_uat_end - datetime(2025, 12, 19)).days) + 'd':^8}")

    # UAT Approval - 1 day after UAT
    uat_approval = add_work_days(frontier_uat_end, 1)
    print(f"  {'Frontier UAT Approval':<40} | {'Dec 19':^12} | {uat_approval.strftime('%b %d'):^12} | {'+' + str((uat_approval - datetime(2025, 12, 19)).days) + 'd':^8}")

    # CAB Approval - after UAT Approval + 1d, 2 working days
    cab_start = add_work_days(uat_approval, 1)
    cab_end = add_work_days(cab_start, 1)  # 2d duration
    print(f"  {'CAB Approval':<40} | {'Jan 06':^12} | {cab_end.strftime('%b %d'):^12} | {'+' + str((cab_end - datetime(2026, 1, 6)).days) + 'd':^8}")

    # Production Deployment - after CAB + 1d
    prod_deploy = add_work_days(cab_end, 1)
    print(f"  {'Production Deployment':<40} | {'Jan 07':^12} | {prod_deploy.strftime('%b %d'):^12} | {'+' + str((prod_deploy - datetime(2026, 1, 7)).days) + 'd':^8}")

    # Gap analysis
    print(f"\n  [GAP ANALYSIS]")
    print(f"    Target Go-Live:        Jan 13, 2026")
    print(f"    Projected Go-Live:     {prod_deploy.strftime('%b %d, %Y')}")
    gap = (prod_deploy - TARGET_GO_LIVE).days
    print(f"    Gap:                   {gap:+d} days")

    if gap > 0:
        print(f"\n  [COMPRESSION NEEDED]")
        print(f"    To hit Jan 13 target, need to compress {gap} days from:")
        print(f"    - UAT Testing duration (currently 5d in SOW)")
        print(f"    - CAB Approval duration (currently 2d)")
        print(f"    - Or overlap activities where possible")

    return prod_deploy, gap


def generate_baseline_update_report(corrections):
    """Generate a detailed report of baseline updates needed"""

    print("\n" + "=" * 90)
    print("  BASELINE UPDATE REPORT - Target: Jan 13, 2026")
    print("=" * 90)

    # Group by update type
    shift_to_jan13 = [c for c in corrections if 'Jan 7 -> Jan 13' in c.get('baseline_action', '')]
    proportional = [c for c in corrections if 'PROPORTIONAL' in c.get('baseline_action', '')]
    keep = [c for c in corrections if 'KEEP' in c.get('baseline_action', '')]

    print(f"\n  Summary:")
    print(f"    Tasks to shift to Jan 13 baseline:  {len(shift_to_jan13)}")
    print(f"    Tasks with proportional shift:      {len(proportional)}")
    print(f"    Tasks to keep (complete):           {len(keep)}")

    if shift_to_jan13:
        print(f"\n  TASKS SHIFTING TO JAN 13 BASELINE:")
        print(f"  {'Row':>4} | {'Task':<45} | {'Current':^12} | {'New':^12}")
        print(f"  {'-'*4}-+-{'-'*45}-+-{'-'*12}-+-{'-'*12}")

        for c in shift_to_jan13:
            curr = c['current_baseline_finish'].strftime('%Y-%m-%d') if c['current_baseline_finish'] else 'N/A'
            new = c['new_baseline_finish'].strftime('%Y-%m-%d') if c['new_baseline_finish'] else 'N/A'
            print(f"  {c['row_number']:>4} | {c['task_name'][:45]:<45} | {curr:^12} | {new:^12}")

    # Show IGT-blocked tasks
    igt_blocked = [c for c in corrections if 'IGT' in c.get('notes', '')]
    if igt_blocked:
        print(f"\n  TASKS BLOCKED BY IGT (will cascade from Dec 23):")
        print(f"  {'Row':>4} | {'Task':<45} | {'Assigned':^10}")
        print(f"  {'-'*4}-+-{'-'*45}-+-{'-'*10}")

        for c in igt_blocked:
            assigned = c['assigned_to'] or 'N/A'
            print(f"  {c['row_number']:>4} | {c['task_name'][:45]:<45} | {assigned:^10}")


def generate_smartsheet_api_script(corrections, tasks):
    """Generate the Python script to update Smartsheet"""

    # First, get column IDs from existing data structure
    # We'll create a script that fetches them first

    script = '''"""
Smartsheet Schedule Update Script
Generated: {timestamp}
Target: Jan 13, 2026 Baseline

This script updates the schedule with corrected baselines.
"""

import smartsheet
import os
from datetime import datetime

# Initialize client
SMARTSHEET_TOKEN = os.environ.get('SMARTSHEET_ACCESS_TOKEN')
if not SMARTSHEET_TOKEN:
    raise ValueError("Set SMARTSHEET_ACCESS_TOKEN environment variable")

client = smartsheet.Smartsheet(SMARTSHEET_TOKEN)
client.errors_as_exceptions(True)

# Sheet ID - UPDATE THIS
SHEET_ID = 0  # <-- Enter your sheet ID here

def get_column_ids():
    """Get column IDs from the sheet"""
    sheet = client.Sheets.get_sheet(SHEET_ID)

    column_map = {{}}
    for col in sheet.columns:
        column_map[col.title] = col.id

    print("Column IDs found:")
    for name, cid in column_map.items():
        print(f"  {{name}}: {{cid}}")

    return column_map

def update_baselines(column_map):
    """Update baseline dates"""

    baseline_finish_col = column_map.get('Baseline Finish')
    baseline_start_col = column_map.get('Baseline Start')

    if not baseline_finish_col:
        print("ERROR: Could not find 'Baseline Finish' column")
        return

    updates = []

    # Baseline updates for Jan 13 target
    baseline_updates = [
'''.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # Add each update
    for c in corrections:
        if c['status'] == 'Complete':
            continue
        if not c.get('new_baseline_finish'):
            continue

        new_finish = c['new_baseline_finish'].strftime('%Y-%m-%d')
        new_start = c['new_baseline_start'].strftime('%Y-%m-%d') if c.get('new_baseline_start') else None

        script += f'''        # Row {c['row_number']}: {c['task_name'][:40]}
        {{
            'row_id': {c['row_id']},
            'baseline_finish': '{new_finish}',
            'baseline_start': {f"'{new_start}'" if new_start else 'None'},
        }},
'''

    script += '''    ]

    # Build row updates
    for update in baseline_updates:
        row = smartsheet.models.Row()
        row.id = update['row_id']

        # Baseline Finish
        row.cells.append({
            'column_id': baseline_finish_col,
            'value': update['baseline_finish']
        })

        # Baseline Start (if provided)
        if update['baseline_start'] and baseline_start_col:
            row.cells.append({
                'column_id': baseline_start_col,
                'value': update['baseline_start']
            })

        updates.append(row)

    # Apply updates in batches of 50
    print(f"Applying {len(updates)} baseline updates...")

    for i in range(0, len(updates), 50):
        batch = updates[i:i+50]
        result = client.Sheets.update_rows(SHEET_ID, batch)
        print(f"  Updated rows {i+1} to {min(i+50, len(updates))}")

    print("Baseline updates complete!")


def main():
    """Main entry point"""
    print("=" * 60)
    print("  SMARTSHEET SCHEDULE UPDATE")
    print("  Target Baseline: Jan 13, 2026")
    print("=" * 60)

    if SHEET_ID == 0:
        print("\\nERROR: Please set the SHEET_ID variable in this script")
        print("You can find it in the sheet URL or properties")
        return

    column_map = get_column_ids()
    update_baselines(column_map)

    print("\\n" + "=" * 60)
    print("  UPDATE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
'''

    return script


def print_summary_report(corrections, projected_date, gap):
    """Print the final summary report"""

    print("\n" + "=" * 90)
    print("  SCHEDULE CORRECTION SUMMARY")
    print("=" * 90)

    print("""
  ROOT CAUSES IDENTIFIED:
  -----------------------
  1. FPS Developer pulled off Voice project (Nov 25 - Dec 9)
     - Impact: 4 working days shift agreed
     - Baseline adjustment: Jan 7 -> Jan 13

  2. IGT SIP Trunks configuration (2-3 weeks vs 1 week)
     - Original due: Dec 8
     - New target: Dec 23
     - Impact: 15 calendar days cascade through critical path

  CORRECTIVE ACTIONS:
  -------------------
  1. UPDATE BASELINES to Jan 13 target
     - All tasks with Jan 7 baseline shift to Jan 13
     - Proportionally adjust earlier milestones

  2. ACCEPT IGT DELAY
     - Dec 23 completion is external dependency
     - SOW Section 9 protects FPS from penalties

  3. RECALCULATE SCHEDULE from IGT completion
     - Forward pass from Dec 23
     - Maintain SOW-contracted durations
""")

    print(f"  PROJECTION RESULTS:")
    print(f"  --------------------")
    print(f"    Target Go-Live:     Jan 13, 2026")
    print(f"    Projected Go-Live:  {projected_date.strftime('%b %d, %Y')}")
    print(f"    Gap:                {gap:+d} days")

    if gap > 0:
        print(f"""
  OPTIONS TO CLOSE GAP:
  ---------------------
  a) Compress UAT (5d -> 3d): Saves 2 days
  b) Compress CAB (2d -> 1d): Saves 1 day
  c) Start UAT early (overlap with FPS QA): Saves 1-2 days
  d) Accept revised go-live of {projected_date.strftime('%b %d')}

  RECOMMENDATION:
  ---------------
  Accept Jan 13 as the baseline and document that:
  - 6 days attributed to FPS developer reassignment (approved)
  - Remaining slip due to IGT external dependency
  - Per SOW Section 9, FPS is not liable for IGT-caused delays
""")

    print("\n  FILES GENERATED:")
    print("  -----------------")
    print("    1. smartsheet_update_jan13.py - API script to update baselines")
    print("    2. Schedule_Corrections_Jan13.xlsx - Detailed correction plan")


def main():
    """Main entry point"""
    print("\n" + "=" * 90)
    print("  SCHEDULE CORRECTION FOR JAN 13, 2026 TARGET")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)

    # Load data
    tasks = load_schedule()
    print(f"\n  Loaded {len(tasks)} tasks from schedule")

    # Calculate critical path dates
    projected_date, gap = calculate_critical_path_dates()

    # Calculate corrections
    corrections = calculate_corrected_schedule(tasks)

    # Generate reports
    generate_baseline_update_report(corrections)

    # Generate Smartsheet update script
    script = generate_smartsheet_api_script(corrections, tasks)
    with open('smartsheet_update_jan13.py', 'w') as f:
        f.write(script)
    print(f"\n  [OK] Generated smartsheet_update_jan13.py")

    # Print summary
    print_summary_report(corrections, projected_date, gap)

    # Save corrections to JSON for Excel generation
    corrections_export = []
    for c in corrections:
        export = {
            'row_number': c['row_number'],
            'row_id': c['row_id'],
            'task_name': c['task_name'],
            'assigned_to': c['assigned_to'],
            'status': c['status'],
            'current_baseline_finish': c['current_baseline_finish'].strftime('%Y-%m-%d') if c['current_baseline_finish'] else None,
            'new_baseline_finish': c['new_baseline_finish'].strftime('%Y-%m-%d') if c.get('new_baseline_finish') else None,
            'baseline_action': c['baseline_action'],
            'notes': c['notes']
        }
        corrections_export.append(export)

    with open('corrections_jan13.json', 'w') as f:
        json.dump(corrections_export, f, indent=2)
    print(f"  [OK] Generated corrections_jan13.json")

    print("\n" + "=" * 90)
    print("  CORRECTION ANALYSIS COMPLETE")
    print("=" * 90 + "\n")

    return corrections, projected_date, gap


if __name__ == "__main__":
    main()
