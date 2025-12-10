"""
Reorder Tasks by Chronological Date - Phase 2 Agentic Voice
Reorders parent tasks within each section by end date, then reassigns WBS numbers

This ensures the schedule reads top-to-bottom in execution order.
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


def parse_date(val):
    """Parse date from various formats"""
    if not val:
        return None
    try:
        if 'T' in str(val):
            return datetime.strptime(str(val).split('T')[0], '%Y-%m-%d')
        return datetime.strptime(str(val), '%Y-%m-%d')
    except:
        return None


def get_sheet_data(client, sheet_id):
    """Get sheet with column map"""
    sheet = client.Sheets.get_sheet(sheet_id)
    col_map = {col.title: col.id for col in sheet.columns}
    return sheet, col_map


def analyze_and_reorder(sheet, col_map):
    """Analyze current order and determine reorder moves"""

    task_col = col_map.get('Tasks')
    end_col = col_map.get('End Date')
    wbs_col = col_map.get('WBS')

    # Build hierarchy
    rows_by_id = {row.id: row for row in sheet.rows}
    children_by_parent = {}
    section_headers = []  # Root level rows (section headers)

    for row in sheet.rows:
        if row.parent_id is None:
            section_headers.append(row)
        else:
            if row.parent_id not in children_by_parent:
                children_by_parent[row.parent_id] = []
            children_by_parent[row.parent_id].append(row)

    # Sort children by row_number to maintain original order
    for parent_id in children_by_parent:
        children_by_parent[parent_id].sort(key=lambda r: r.row_number)

    moves = []  # List of (row_id, sibling_id) to position row after sibling

    for section_row in section_headers:
        section_name = None
        for cell in section_row.cells:
            if cell.column_id == task_col:
                section_name = cell.value
                break

        print(f"\n  Section: {section_name}")
        print(f"  {'-'*60}")

        # Get direct children (parent tasks) of this section
        parent_tasks = children_by_parent.get(section_row.id, [])

        # Build list with dates for sorting
        tasks_with_dates = []
        for parent_row in parent_tasks:
            task_name = end_date = None
            for cell in parent_row.cells:
                if cell.column_id == task_col:
                    task_name = cell.value
                elif cell.column_id == end_col:
                    end_date = parse_date(cell.value)

            tasks_with_dates.append({
                'row': parent_row,
                'row_id': parent_row.id,
                'task': task_name,
                'end_date': end_date,
                'current_pos': parent_row.row_number
            })

        # Current order
        current_order = [t['row_id'] for t in tasks_with_dates]

        # Optimal order (by end date, None dates at end)
        sorted_tasks = sorted(
            tasks_with_dates,
            key=lambda x: (x['end_date'] is None, x['end_date'] or datetime.max)
        )
        optimal_order = [t['row_id'] for t in sorted_tasks]

        if current_order == optimal_order:
            print(f"  [OK] Already in chronological order")
            for t in tasks_with_dates:
                end_str = t['end_date'].strftime('%Y-%m-%d') if t['end_date'] else '(none)'
                print(f"    Row {t['current_pos']:>2}: {end_str} - {t['task'][:40]}")
        else:
            print(f"  [!] Needs reordering:")
            print(f"\n  Current order:")
            for t in tasks_with_dates:
                end_str = t['end_date'].strftime('%Y-%m-%d') if t['end_date'] else '(none)'
                print(f"    Row {t['current_pos']:>2}: {end_str} - {t['task'][:40]}")

            print(f"\n  Optimal order (by end date):")
            for i, t in enumerate(sorted_tasks):
                end_str = t['end_date'].strftime('%Y-%m-%d') if t['end_date'] else '(none)'
                print(f"    Pos {i+1:>2}: {end_str} - {t['task'][:40]}")

            # Calculate moves needed
            # We'll move each row to its correct position under the section header
            for i, t in enumerate(sorted_tasks):
                if i == 0:
                    # First task should be directly under section header
                    moves.append({
                        'row_id': t['row_id'],
                        'parent_id': section_row.id,
                        'sibling_id': None,  # First child
                        'task': t['task']
                    })
                else:
                    # Position after the previous task
                    prev_task = sorted_tasks[i-1]
                    moves.append({
                        'row_id': t['row_id'],
                        'parent_id': section_row.id,
                        'sibling_id': prev_task['row_id'],
                        'task': t['task']
                    })

    return moves


def apply_reorder(client, sheet_id, moves, dry_run=True):
    """Apply the reorder moves"""

    print("\n" + "=" * 80)
    if dry_run:
        print("  REORDER PREVIEW (DRY RUN)")
    else:
        print("  APPLYING REORDER")
    print("=" * 80)

    if not moves:
        print("\n  No reordering needed - all sections are in chronological order")
        return

    print(f"\n  Moves to apply: {len(moves)}")

    for move in moves:
        sibling_info = f"after row {move['sibling_id']}" if move['sibling_id'] else "as first child"
        print(f"    Move '{move['task'][:35]}' -> {sibling_info}")

    if dry_run:
        print("\n  [DRY RUN] Run without --dry-run to apply these changes")
        return

    # Apply moves one at a time to maintain order
    import time
    for i, move in enumerate(moves):
        row_update = smartsheet.models.Row()
        row_update.id = move['row_id']

        if move['sibling_id']:
            # Position below the sibling
            row_update.sibling_id = move['sibling_id']
        else:
            # First child under parent - use parent_id with to_top
            row_update.parent_id = move['parent_id']
            row_update.to_top = True

        try:
            result = client.Sheets.update_rows(sheet_id, [row_update])
            print(f"  [{i+1}/{len(moves)}] Moved: {move['task'][:40]}")
            time.sleep(0.5)  # Small delay to avoid rate limiting
        except Exception as e:
            print(f"  [ERROR] Failed to move '{move['task'][:40]}': {e}")
            raise

    print(f"\n  [OK] Applied {len(moves)} row moves")


def recalculate_wbs(client, sheet_id):
    """Recalculate WBS values after reordering"""

    print("\n" + "=" * 80)
    print("  RECALCULATING WBS VALUES")
    print("=" * 80)

    sheet, col_map = get_sheet_data(client, sheet_id)
    task_col = col_map.get('Tasks')
    wbs_col = col_map.get('WBS')

    if not wbs_col:
        print("  [ERROR] WBS column not found")
        return

    # Build hierarchy
    children_by_parent = {}
    root_rows = []

    for row in sheet.rows:
        if row.parent_id is None:
            root_rows.append(row)
        else:
            if row.parent_id not in children_by_parent:
                children_by_parent[row.parent_id] = []
            children_by_parent[row.parent_id].append(row)

    root_rows.sort(key=lambda r: r.row_number)
    for parent_id in children_by_parent:
        children_by_parent[parent_id].sort(key=lambda r: r.row_number)

    wbs_values = {}

    def assign_wbs(row, prefix, is_section_header=False):
        wbs_values[row.id] = prefix
        children = children_by_parent.get(row.id, [])
        for i, child in enumerate(children, 1):
            if is_section_header:
                child_wbs = f"{prefix[0]}.{i}"
            else:
                child_wbs = f"{prefix}.{i}"
            assign_wbs(child, child_wbs, is_section_header=False)

    for i, root_row in enumerate(root_rows, 1):
        assign_wbs(root_row, f"{i}.0", is_section_header=True)

    # Build updates
    updates = []
    for row in sheet.rows:
        wbs = wbs_values.get(row.id)
        if wbs:
            row_update = smartsheet.models.Row()
            row_update.id = row.id
            cell = smartsheet.models.Cell()
            cell.column_id = wbs_col
            cell.value = wbs
            row_update.cells.append(cell)
            updates.append(row_update)

    # Apply in batches
    batch_size = 50
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        result = client.Sheets.update_rows(sheet_id, batch)
        print(f"  Updated WBS batch {i//batch_size + 1}: {len(batch)} rows")

    print(f"\n  [OK] Recalculated {len(updates)} WBS values")


def show_final_structure(client, sheet_id):
    """Show the final structure after reordering"""

    print("\n" + "=" * 80)
    print("  FINAL STRUCTURE")
    print("=" * 80)

    sheet, col_map = get_sheet_data(client, sheet_id)
    task_col = col_map.get('Tasks')
    wbs_col = col_map.get('WBS')
    end_col = col_map.get('End Date')

    print(f"\n  {'WBS':<10} | {'End Date':<12} | {'Task':<50}")
    print(f"  {'-'*10}-+-{'-'*12}-+-{'-'*50}")

    for row in sheet.rows:
        wbs = task = end_date = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value
            elif cell.column_id == end_col:
                end_date = parse_date(cell.value)

        if not wbs:
            continue

        depth = wbs.count('.')
        if depth <= 1:  # Only show section headers and parent tasks
            indent = "  " * (depth - 1) if depth > 1 else ""
            end_str = end_date.strftime('%Y-%m-%d') if end_date else '(none)'
            task_str = f"{indent}{task[:48-len(indent)]}" if task else "(empty)"
            print(f"  {wbs:<10} | {end_str:<12} | {task_str:<50}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Reorder tasks by chronological date')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  REORDER BY CHRONOLOGICAL DATE - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")
    print(f"  [OK] Sheet ID: {TASK_SHEET_ID}")

    sheet, col_map = get_sheet_data(client, TASK_SHEET_ID)
    print(f"  [OK] Loaded {len(sheet.rows)} rows")

    # Analyze and determine moves
    print("\n  Analyzing current order...")
    moves = analyze_and_reorder(sheet, col_map)

    # Apply reorder
    apply_reorder(client, TASK_SHEET_ID, moves, dry_run=args.dry_run)

    # Recalculate WBS if not dry run
    if not args.dry_run and moves:
        recalculate_wbs(client, TASK_SHEET_ID)
        show_final_structure(client, TASK_SHEET_ID)

    print("\n" + "=" * 80)
    print("  COMPLETE")
    print("=" * 80)

    if args.dry_run:
        print("\n  To apply changes, run: python reorder_by_date.py")

    print()


if __name__ == "__main__":
    main()
