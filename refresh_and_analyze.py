"""
Refresh Schedule Data and Analyze New Timeline
For 12/10 Morning Standup

1. Refresh data from Smartsheet
2. Add note to Row 25 (IGT Signal API)
3. Generate standup summary
"""

import smartsheet
import json
from datetime import datetime
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


def get_client():
    """Initialize Smartsheet client"""
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)
    return client


def refresh_data(client, sheet_id):
    """Refresh data from Smartsheet"""
    sheet = client.Sheets.get_sheet(sheet_id)

    column_map = {}
    for col in sheet.columns:
        column_map[col.title] = col.id

    tasks = []
    for row in sheet.rows:
        task = {
            'row_number': row.row_number,
            'row_id': row.id,
            'parent_id': row.parent_id
        }
        for cell in row.cells:
            # Find column name
            for col_name, col_id in column_map.items():
                if col_id == cell.column_id:
                    task[col_name] = cell.value
                    break
        tasks.append(task)

    return tasks, column_map, sheet


def parse_date(date_str):
    """Parse date string"""
    if not date_str:
        return None
    try:
        if 'T' in str(date_str):
            return datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d')
        return datetime.strptime(str(date_str), '%Y-%m-%d')
    except:
        return None


def add_igt_note(client, sheet_id, tasks, column_map):
    """Add note to Row 25 about IGT delay"""
    notes_col = column_map.get('Notes')

    # Find Row 25
    row_25 = None
    for task in tasks:
        if task['row_number'] == 25:
            row_25 = task
            break

    if not row_25:
        print("  [WARN] Row 25 not found")
        return

    current_notes = row_25.get('Notes', '') or ''
    new_note = "12/09 - Per Sandeep (IGT): Configuration will take 2-3 weeks, targeting Dec 23 completion."

    # Check if note already exists
    if "Dec 23" in current_notes:
        print(f"  Row 25: Note already present - skipping")
        return

    # Append note
    if current_notes:
        updated_notes = f"{current_notes}\n{new_note}"
    else:
        updated_notes = new_note

    # Update
    row_update = smartsheet.models.Row()
    row_update.id = row_25['row_id']
    cell = smartsheet.models.Cell()
    cell.column_id = notes_col
    cell.value = updated_notes
    row_update.cells.append(cell)

    result = client.Sheets.update_rows(sheet_id, [row_update])
    print(f"  [OK] Row 25: Added IGT delay note")


def analyze_timeline(tasks):
    """Analyze the new timeline"""
    print("\n" + "=" * 80)
    print("  REFRESHED TIMELINE ANALYSIS")
    print(f"  As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Find key milestone dates
    milestones = {}
    critical_path = []

    for task in tasks:
        name = task.get('Tasks', '')
        end_date = parse_date(task.get('End Date'))
        baseline = parse_date(task.get('Baseline Finish'))
        variance = task.get('Variance')
        status = task.get('Status', '')
        health = task.get('Health', '')
        row = task['row_number']

        # Key milestones
        if 'FPS Production Deployment' in name and row == 72:
            milestones['go_live'] = {'date': end_date, 'baseline': baseline, 'row': row}
        if 'IGT Staging Dependencies Complete' in name:
            milestones['igt_staging'] = {'date': end_date, 'row': row}
        if 'FPS QA Testing' in name and row == 40:
            milestones['fps_qa'] = {'date': end_date, 'row': row}
        if 'Frontier UAT Testing' in name and row == 56:
            milestones['frontier_uat'] = {'date': end_date, 'row': row}
        if 'Frontier UAT Approval' in name and row == 62:
            milestones['uat_approval'] = {'date': end_date, 'row': row}
        if 'CAB' in name and row == 69:
            milestones['cab'] = {'date': end_date, 'row': row}

        # Build critical path (tasks with end dates driving go-live)
        if end_date and status != 'Complete':
            critical_path.append({
                'row': row,
                'task': name,
                'end_date': end_date,
                'baseline': baseline,
                'variance': variance,
                'health': health,
                'assigned': task.get('Assigned To', '')
            })

    # Sort by end date descending to find latest tasks
    critical_path.sort(key=lambda x: x['end_date'], reverse=True)

    # Print key dates
    print("\n  KEY MILESTONE DATES (Post-Update):")
    print(f"  {'-'*60}")

    target = datetime(2026, 1, 13)
    original_baseline = datetime(2026, 1, 7)

    go_live = milestones.get('go_live', {})
    go_live_date = go_live.get('date')

    if go_live_date:
        gap_to_target = (go_live_date - target).days
        print(f"  Go-Live (Row 72):        {go_live_date.strftime('%Y-%m-%d')} | Gap to Jan 13: {gap_to_target:+d} days")

    for key, label in [
        ('cab', 'CAB Approval (Row 69)'),
        ('uat_approval', 'UAT Approval (Row 62)'),
        ('frontier_uat', 'Frontier UAT (Row 56)'),
        ('fps_qa', 'FPS QA (Row 40)'),
        ('igt_staging', 'IGT Staging (Row 22)')
    ]:
        m = milestones.get(key, {})
        if m.get('date'):
            print(f"  {label:26} {m['date'].strftime('%Y-%m-%d')}")

    return milestones, critical_path, go_live_date


def find_new_variance_issues(tasks, old_data_file='sheet_data_audit.json'):
    """Find tasks with new negative variance"""
    print("\n  VARIANCE CHANGE ANALYSIS:")
    print(f"  {'-'*60}")

    # Load old data for comparison
    try:
        with open(old_data_file, 'r') as f:
            old_tasks = json.load(f)
        old_by_row = {t['row_number']: t for t in old_tasks}
    except:
        print("  [WARN] Could not load previous data for comparison")
        return []

    new_issues = []

    for task in tasks:
        row = task['row_number']
        name = task.get('Tasks', '')
        new_variance = task.get('Variance')
        status = task.get('Status', '')

        if status == 'Complete':
            continue

        old_task = old_by_row.get(row, {})
        old_variance = old_task.get('Variance')

        # Check for new negative variance
        if new_variance is not None and new_variance < 0:
            if old_variance is None or old_variance >= 0:
                new_issues.append({
                    'row': row,
                    'task': name,
                    'old_variance': old_variance,
                    'new_variance': new_variance,
                    'assigned': task.get('Assigned To', '')
                })

    if new_issues:
        print(f"\n  Tasks with NEW Negative Variance ({len(new_issues)}):")
        for issue in new_issues[:10]:
            old_v = f"{issue['old_variance']:.0f}" if issue['old_variance'] is not None else "N/A"
            new_v = f"{issue['new_variance']:.0f}"
            print(f"    Row {issue['row']:2}: {old_v:>5} -> {new_v:>5} | {issue['assigned']:10} | {issue['task'][:35]}")
    else:
        print("  No new negative variance issues detected")

    return new_issues


def generate_standup_summary(milestones, critical_path, go_live_date, new_issues):
    """Generate standup summary"""
    print("\n")
    print("=" * 80)
    print("  STANDUP SUMMARY - Phase 2 Agentic Voice")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d')} | For: 12/10 Morning Call")
    print("=" * 80)

    # Old vs New Go-Live
    print("\n  GO-LIVE DATE COMPARISON")
    print(f"  {'-'*40}")

    original_baseline = datetime(2026, 1, 7)
    approved_target = datetime(2026, 1, 13)
    previous_projection = datetime(2026, 1, 30)  # Before today's updates

    print(f"  Original SOW Baseline:    Jan 7, 2026")
    print(f"  Approved Target:          Jan 13, 2026")
    print(f"  Previous Projection:      Jan 30, 2026")
    if go_live_date:
        print(f"  NEW Projection:           {go_live_date.strftime('%b %d, %Y')}")
        improvement = (previous_projection - go_live_date).days
        gap = (go_live_date - approved_target).days
        print(f"  Improvement:              {improvement:+d} days from previous")
        print(f"  Gap to Target:            {gap:+d} days")

    # Top Critical Path Items
    print("\n  TOP 5 CRITICAL PATH DRIVERS")
    print(f"  {'-'*40}")

    # Filter to parent-level tasks (those with meaningful names)
    parent_tasks = [t for t in critical_path if not any(
        x in t['task'].lower() for x in ['validate', 'execute', 'perform', 'obtain', 'provision', 'set up', 'configure', 'secure', 'present']
    ) or t['row'] in [22, 40, 56, 62, 69, 72]]

    shown = set()
    count = 0
    for task in critical_path:
        # Show only key milestones
        if task['row'] in [22, 40, 56, 62, 69, 72] and task['row'] not in shown:
            shown.add(task['row'])
            end = task['end_date'].strftime('%b %d')
            health = task['health'] or 'N/A'
            assigned = task['assigned'] or 'N/A'
            print(f"  {count+1}. Row {task['row']:2} | {end} | {health:6} | {assigned:10} | {task['task'][:30]}")
            count += 1
            if count >= 5:
                break

    # New Variance Issues
    print("\n  NEW VARIANCE CONCERNS")
    print(f"  {'-'*40}")
    if new_issues:
        for issue in new_issues[:5]:
            print(f"  - Row {issue['row']}: {issue['task'][:40]} ({issue['new_variance']:.0f}d)")
    else:
        print("  No new negative variance issues after predecessor fixes")

    # Action Items
    print("\n  ACTION ITEMS FROM 12/09 UPDATE")
    print(f"  {'-'*40}")
    print("  [DONE] Baselines updated to Jan 13 target (54 rows)")
    print("  [DONE] Predecessor dependencies corrected (22 rows)")
    print("  [DONE] Compression candidates flagged (9 tasks)")
    print("  [DONE] CSG status updated to In Progress (3 tasks)")
    print("  [DONE] IGT delay documented in Row 25")
    print("  [TODO] Review structure: Move Rows 46-55 to Production section")

    # Key Risks
    print("\n  KEY RISKS")
    print(f"  {'-'*40}")
    print("  1. IGT SIP Trunks (Row 22-27) - Dec 23 target is critical path")
    print("  2. Holiday impact (Dec 24-26) - No working days")
    print("  3. FPS Developer just returned (12/9) - velocity TBD")

    print("\n" + "=" * 80)
    print("  END OF SUMMARY")
    print("=" * 80)

    # Save summary to file
    summary = {
        'generated': datetime.now().isoformat(),
        'go_live': {
            'original_baseline': '2026-01-07',
            'approved_target': '2026-01-13',
            'previous_projection': '2026-01-30',
            'new_projection': go_live_date.strftime('%Y-%m-%d') if go_live_date else None,
        },
        'critical_path': [
            {'row': t['row'], 'task': t['task'], 'date': t['end_date'].strftime('%Y-%m-%d')}
            for t in critical_path[:10]
        ],
        'new_variance_issues': new_issues[:10],
        'updates_applied': {
            'baselines': 54,
            'predecessors': 22,
            'compression_notes': 9,
            'status_updates': 3
        }
    }

    with open('standup_summary_12_10.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n  [OK] Summary saved to standup_summary_12_10.json")


def save_refreshed_data(tasks):
    """Save refreshed data"""
    filename = f"sheet_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(tasks, f, indent=2, default=str)
    print(f"  [OK] Refreshed data saved to {filename}")
    return filename


def main():
    print("\n" + "=" * 80)
    print("  REFRESH AND ANALYZE - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Initialize
    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")

    # Refresh data
    print(f"\n  Refreshing data from Sheet ID: {TASK_SHEET_ID}")
    tasks, column_map, sheet = refresh_data(client, TASK_SHEET_ID)
    print(f"  [OK] Loaded {len(tasks)} tasks")

    # Add IGT note to Row 25
    print(f"\n  Adding IGT delay note to Row 25...")
    add_igt_note(client, TASK_SHEET_ID, tasks, column_map)

    # Analyze timeline
    milestones, critical_path, go_live_date = analyze_timeline(tasks)

    # Find new variance issues
    new_issues = find_new_variance_issues(tasks)

    # Generate standup summary
    generate_standup_summary(milestones, critical_path, go_live_date, new_issues)

    # Save refreshed data
    save_refreshed_data(tasks)

    print("\n")


if __name__ == "__main__":
    main()
