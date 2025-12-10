"""
Smartsheet Baseline Update Script
Target: January 13, 2026

This script updates baselines in the Smartsheet to reflect the approved target.

Usage:
    python update_smartsheet_baselines.py --dry-run    # Preview changes
    python update_smartsheet_baselines.py              # Apply changes
"""

import argparse
import json
import smartsheet
from datetime import datetime, timedelta
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


# Target dates
TARGET_GO_LIVE = datetime(2026, 1, 13)
ORIGINAL_BASELINE = datetime(2026, 1, 7)
BASELINE_SHIFT_DAYS = 6


def get_client():
    """Initialize Smartsheet client"""
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)
    return client


def get_column_map(client, sheet_id):
    """Get column name to ID mapping"""
    sheet = client.Sheets.get_sheet(sheet_id)
    column_map = {}
    for col in sheet.columns:
        column_map[col.title] = col.id
    return column_map, sheet


def backup_sheet(client, sheet_id):
    """Export current sheet data as backup"""
    sheet = client.Sheets.get_sheet(sheet_id)

    backup = {
        'timestamp': datetime.now().isoformat(),
        'sheet_name': sheet.name,
        'sheet_id': sheet_id,
        'rows': []
    }

    for row in sheet.rows:
        row_data = {
            'row_id': row.id,
            'row_number': row.row_number,
            'cells': []
        }
        for cell in row.cells:
            row_data['cells'].append({
                'column_id': cell.column_id,
                'value': cell.value,
                'display_value': cell.display_value
            })
        backup['rows'].append(row_data)

    filename = f"backup_{sheet_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(backup, f, indent=2, default=str)

    print(f"[BACKUP] Saved to {filename}")
    return filename


def parse_date(date_val):
    """Parse date from various formats"""
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val
    try:
        date_str = str(date_val)
        if 'T' in date_str:
            return datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return None


def calculate_baseline_updates(sheet, column_map):
    """Calculate which rows need baseline updates"""

    baseline_finish_col = column_map.get('Baseline Finish')
    baseline_start_col = column_map.get('Baseline Start')
    status_col = column_map.get('Status')
    task_col = column_map.get('Tasks')

    if not baseline_finish_col:
        raise ValueError("Could not find 'Baseline Finish' column")

    updates = []

    for row in sheet.rows:
        # Get cell values
        task_name = None
        status = None
        baseline_finish = None
        baseline_start = None

        for cell in row.cells:
            if cell.column_id == task_col:
                task_name = cell.value
            elif cell.column_id == status_col:
                status = cell.value
            elif cell.column_id == baseline_finish_col:
                baseline_finish = parse_date(cell.value)
            elif cell.column_id == baseline_start_col:
                baseline_start = parse_date(cell.value)

        # Skip completed tasks
        if status == 'Complete':
            continue

        # Skip if no baseline
        if not baseline_finish:
            continue

        # Calculate new baseline
        new_baseline_finish = None
        new_baseline_start = None
        action = None

        # Check if baseline matches original Jan 7 target
        if baseline_finish.date() == ORIGINAL_BASELINE.date():
            new_baseline_finish = TARGET_GO_LIVE
            action = "SHIFT Jan 7 -> Jan 13"
            if baseline_start:
                new_baseline_start = baseline_start + timedelta(days=BASELINE_SHIFT_DAYS)

        # Proportionally shift earlier baselines
        elif baseline_finish < ORIGINAL_BASELINE:
            days_before = (ORIGINAL_BASELINE - baseline_finish).days
            new_baseline_finish = TARGET_GO_LIVE - timedelta(days=days_before)
            action = f"PROPORTIONAL (+{BASELINE_SHIFT_DAYS}d)"
            if baseline_start:
                new_baseline_start = baseline_start + timedelta(days=BASELINE_SHIFT_DAYS)

        if new_baseline_finish:
            updates.append({
                'row_id': row.id,
                'row_number': row.row_number,
                'task_name': task_name or f'Row {row.row_number}',
                'current_baseline_finish': baseline_finish,
                'new_baseline_finish': new_baseline_finish,
                'current_baseline_start': baseline_start,
                'new_baseline_start': new_baseline_start,
                'action': action
            })

    return updates


def apply_updates(client, sheet_id, updates, column_map, dry_run=True):
    """Apply baseline updates to Smartsheet"""

    baseline_finish_col = column_map.get('Baseline Finish')
    baseline_start_col = column_map.get('Baseline Start')

    if dry_run:
        print("\n" + "=" * 70)
        print("  DRY RUN - No changes will be made")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("  APPLYING UPDATES")
        print("=" * 70)

    print(f"\n  Updates to apply: {len(updates)}")
    print(f"\n  {'Row':>4} | {'Task':<40} | {'Current':^12} | {'New':^12}")
    print(f"  {'-'*4}-+-{'-'*40}-+-{'-'*12}-+-{'-'*12}")

    for u in updates:
        curr = u['current_baseline_finish'].strftime('%Y-%m-%d')
        new = u['new_baseline_finish'].strftime('%Y-%m-%d')
        print(f"  {u['row_number']:>4} | {u['task_name'][:40]:<40} | {curr:^12} | {new:^12}")

    if dry_run:
        print("\n  [DRY RUN] Run without --dry-run to apply these changes")
        return

    # Build row updates
    rows_to_update = []

    for u in updates:
        row = smartsheet.models.Row()
        row.id = u['row_id']

        # Baseline Finish
        cell_finish = smartsheet.models.Cell()
        cell_finish.column_id = baseline_finish_col
        cell_finish.value = u['new_baseline_finish'].strftime('%Y-%m-%d')
        row.cells.append(cell_finish)

        # Baseline Start (if applicable)
        if u.get('new_baseline_start') and baseline_start_col:
            cell_start = smartsheet.models.Cell()
            cell_start.column_id = baseline_start_col
            cell_start.value = u['new_baseline_start'].strftime('%Y-%m-%d')
            row.cells.append(cell_start)

        rows_to_update.append(row)

    # Apply in batches of 50
    batch_size = 50
    total_updated = 0

    for i in range(0, len(rows_to_update), batch_size):
        batch = rows_to_update[i:i + batch_size]
        try:
            result = client.Sheets.update_rows(sheet_id, batch)
            total_updated += len(batch)
            print(f"  Updated batch {i//batch_size + 1}: {len(batch)} rows")
        except Exception as e:
            print(f"  ERROR updating batch {i//batch_size + 1}: {e}")
            raise

    print(f"\n  [SUCCESS] Updated {total_updated} rows")


def print_summary(updates):
    """Print update summary"""

    print("\n" + "=" * 70)
    print("  UPDATE SUMMARY")
    print("=" * 70)

    # Group by action type
    jan7_shifts = [u for u in updates if 'Jan 7' in u['action']]
    proportional = [u for u in updates if 'PROPORTIONAL' in u['action']]

    print(f"\n  Baselines shifting Jan 7 -> Jan 13: {len(jan7_shifts)}")
    print(f"  Proportionally adjusted baselines: {len(proportional)}")
    print(f"  Total updates: {len(updates)}")

    if jan7_shifts:
        print(f"\n  Tasks at Jan 7 baseline (final deployment):")
        for u in jan7_shifts[:5]:
            print(f"    Row {u['row_number']}: {u['task_name'][:50]}")
        if len(jan7_shifts) > 5:
            print(f"    ... and {len(jan7_shifts) - 5} more")


def main():
    parser = argparse.ArgumentParser(description='Update Smartsheet baselines to Jan 13 target')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup (not recommended)')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  SMARTSHEET BASELINE UPDATE")
    print("  Target: January 13, 2026")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Initialize client
    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")
    print(f"  [OK] Sheet ID: {TASK_SHEET_ID}")

    # Backup first
    if not args.no_backup and not args.dry_run:
        backup_sheet(client, TASK_SHEET_ID)

    # Get column mapping
    column_map, sheet = get_column_map(client, TASK_SHEET_ID)
    print(f"  [OK] Found {len(column_map)} columns")

    # Calculate updates
    updates = calculate_baseline_updates(sheet, column_map)
    print(f"  [OK] Calculated {len(updates)} baseline updates")

    # Print summary
    print_summary(updates)

    # Apply updates
    apply_updates(client, TASK_SHEET_ID, updates, column_map, dry_run=args.dry_run)

    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
