"""
Add WBS (Work Breakdown Structure) Column - Phase 2 Agentic Voice
Creates a stable index for task ordering and predecessor references

WBS Format:
  1.0   Development Phase (Section Header)
  1.1     CSG: Staging Setup (Parent Task)
  1.1.1     Sub-task
  1.2     Next Parent Task
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


def get_or_create_wbs_column(client, sheet_id):
    """Get existing WBS column or create a new one"""
    sheet = client.Sheets.get_sheet(sheet_id)

    # Check if WBS column exists
    for col in sheet.columns:
        if col.title == 'WBS':
            print(f"  [OK] WBS column exists (ID: {col.id})")
            return col.id, sheet

    # Create WBS column - add it as the first column after Tasks
    task_col_index = 0
    for i, col in enumerate(sheet.columns):
        if col.title == 'Tasks':
            task_col_index = i
            break

    new_column = smartsheet.models.Column({
        'title': 'WBS',
        'type': 'TEXT_NUMBER',
        'index': task_col_index + 1  # Insert after Tasks column
    })

    result = client.Sheets.add_columns(sheet_id, [new_column])
    wbs_col_id = result.data[0].id
    print(f"  [OK] Created WBS column (ID: {wbs_col_id})")

    # Refresh sheet to get updated structure
    sheet = client.Sheets.get_sheet(sheet_id)
    return wbs_col_id, sheet


def calculate_wbs_values(sheet):
    """Calculate WBS values based on hierarchy with proper format"""

    task_col_id = sheet.columns[0].id

    # Build parent-child relationships
    rows_by_id = {row.id: row for row in sheet.rows}
    children_by_parent = {}  # parent_id -> [child_rows]
    root_rows = []

    for row in sheet.rows:
        if row.parent_id is None:
            root_rows.append(row)
        else:
            if row.parent_id not in children_by_parent:
                children_by_parent[row.parent_id] = []
            children_by_parent[row.parent_id].append(row)

    # Sort root rows by row_number
    root_rows.sort(key=lambda r: r.row_number)

    # Sort children by row_number
    for parent_id in children_by_parent:
        children_by_parent[parent_id].sort(key=lambda r: r.row_number)

    wbs_values = {}  # row_id -> wbs_string

    def assign_wbs(row, prefix, is_section_header=False):
        """Recursively assign WBS to row and its children"""
        wbs_values[row.id] = prefix

        children = children_by_parent.get(row.id, [])
        for i, child in enumerate(children, 1):
            if is_section_header:
                # Direct children of section headers get X.Y format
                child_wbs = f"{prefix[0]}.{i}"
            else:
                # Grandchildren get X.Y.Z format
                child_wbs = f"{prefix}.{i}"

            assign_wbs(child, child_wbs, is_section_header=False)

    # Assign WBS starting from root rows (section headers)
    for i, root_row in enumerate(root_rows, 1):
        assign_wbs(root_row, f"{i}.0", is_section_header=True)

    return wbs_values


def validate_structure(sheet, wbs_values):
    """Validate structure and identify issues"""

    task_col_id = sheet.columns[0].id
    issues = []

    # Build lookups
    rows_by_id = {row.id: row for row in sheet.rows}

    # Define expected section for each task type
    production_keywords = ['Production Setup', 'Production Deployment', 'CAB Approval']
    qa_keywords = ['QA Testing', 'UAT Testing', 'UAT Approval']
    dev_keywords = ['Staging Setup', 'Development', 'Proposal', 'SOW']

    for row in sheet.rows:
        task_name = None
        for cell in row.cells:
            if cell.column_id == task_col_id:
                task_name = cell.value
                break

        if not task_name:
            continue

        wbs = wbs_values.get(row.id, '')
        section_num = wbs.split('.')[0] if wbs else ''

        # Check for misplaced tasks
        if any(kw in task_name for kw in production_keywords):
            if section_num != '3':
                issues.append({
                    'row': row.row_number,
                    'wbs': wbs,
                    'task': task_name,
                    'issue': f'Production task in section {section_num}, should be in section 3',
                    'severity': 'HIGH'
                })
        elif any(kw in task_name for kw in qa_keywords):
            if section_num != '2':
                issues.append({
                    'row': row.row_number,
                    'wbs': wbs,
                    'task': task_name,
                    'issue': f'QA/UAT task in section {section_num}, should be in section 2',
                    'severity': 'MEDIUM'
                })

    return issues


def apply_wbs_values(client, sheet_id, sheet, wbs_col_id, wbs_values, dry_run=True):
    """Apply WBS values to the sheet"""

    task_col_id = sheet.columns[0].id

    print("\n" + "=" * 80)
    print("  WBS ASSIGNMENTS")
    print("=" * 80)
    print(f"\n  {'WBS':<10} | {'Row':>4} | {'Task Name':<55}")
    print(f"  {'-'*10}-+-{'-'*4}-+-{'-'*55}")

    updates = []

    for row in sheet.rows:
        wbs = wbs_values.get(row.id)
        if not wbs:
            continue

        # Get task name for display
        task_name = None
        for cell in row.cells:
            if cell.column_id == task_col_id:
                task_name = cell.value
                break

        # Indent based on WBS depth
        depth = wbs.count('.')
        indent = "  " * (depth - 1) if depth > 1 else ""
        display_name = f"{indent}{task_name[:53-len(indent)]}" if task_name else "(empty)"

        print(f"  {wbs:<10} | {row.row_number:>4} | {display_name:<55}")

        # Create row update
        row_update = smartsheet.models.Row()
        row_update.id = row.id
        cell = smartsheet.models.Cell()
        cell.column_id = wbs_col_id
        cell.value = wbs
        row_update.cells.append(cell)
        updates.append(row_update)

    print("\n" + "=" * 80)

    if dry_run:
        print("  DRY RUN - No changes applied")
        print("=" * 80)
        print(f"\n  Total rows to update: {len(updates)}")
        print(f"  Run without --dry-run to apply these changes")
    else:
        print("  APPLYING WBS VALUES")
        print("=" * 80)

        if updates:
            # Apply in batches
            batch_size = 50
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                try:
                    result = client.Sheets.update_rows(sheet_id, batch)
                    print(f"  Updated batch {i//batch_size + 1}: {len(batch)} rows")
                except Exception as e:
                    print(f"  ERROR in batch {i//batch_size + 1}: {e}")
                    raise

            print(f"\n  [OK] Applied WBS values to {len(updates)} rows")
        else:
            print("\n  No updates needed")

    return updates


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Add WBS column to Smartsheet')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  ADD WBS COLUMN - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Initialize
    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")
    print(f"  [OK] Sheet ID: {TASK_SHEET_ID}")

    # Get or create WBS column
    print(f"\n  Checking for WBS column...")
    wbs_col_id, sheet = get_or_create_wbs_column(client, TASK_SHEET_ID)

    # Calculate WBS values
    print(f"\n  Calculating WBS values based on hierarchy...")
    wbs_values = calculate_wbs_values(sheet)
    print(f"  [OK] Calculated {len(wbs_values)} WBS values")

    # Validate structure
    print(f"\n  Validating structure...")
    issues = validate_structure(sheet, wbs_values)

    if issues:
        print("\n" + "=" * 80)
        print("  STRUCTURE ISSUES DETECTED")
        print("=" * 80)
        for issue in issues:
            print(f"\n  [{issue['severity']}] Row {issue['row']} (WBS {issue['wbs']})")
            print(f"    Task: {issue['task'][:60]}")
            print(f"    Issue: {issue['issue']}")
    else:
        print(f"  [OK] No structure issues detected")

    # Apply WBS values
    apply_wbs_values(client, TASK_SHEET_ID, sheet, wbs_col_id, wbs_values, dry_run=args.dry_run)

    print("\n" + "=" * 80)
    print("  COMPLETE")
    print("=" * 80)

    if args.dry_run:
        print("\n  To apply changes, run: python add_wbs_column.py")

    print()


if __name__ == "__main__":
    main()
