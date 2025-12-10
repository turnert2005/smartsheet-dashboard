"""
Task Nomenclature Standardization - Phase 2 Agentic Voice
Applies agreed-upon naming convention to parent tasks

Pattern: [Vendor]: [Environment/Phase] [Action Type]
Action Types: Setup, Development, Testing, Approval
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


def get_column_map(client, sheet_id):
    """Get column name to ID mapping"""
    sheet = client.Sheets.get_sheet(sheet_id)
    column_map = {}
    for col in sheet.columns:
        column_map[col.title] = col.id
    return column_map, sheet


# Nomenclature mapping: current_name -> new_standardized_name
# Based on agreed pattern: [Vendor]: [Environment/Phase] [Action Type]
NOMENCLATURE_UPDATES = {
    # Development Phase parent tasks
    "CSG Staging Dependencies Complete (Testing)": "CSG: Staging Setup",
    "Cognigy Staging Dependencies Phase 1": "Cognigy: Staging Setup Phase 1",
    "Cognigy Staging Dependencies Phase 2": "Cognigy: Staging Setup Phase 2",
    "IGT Staging Dependencies Complete": "IGT: Staging Setup",
    "FPS Development - Knowledgebase": "FPS: Knowledgebase Development",
    "FPS Development - Partner Integrations": "FPS: Partner Integrations Development",

    # Note: Frontier Staging Dependencies and Frontier Production Dependencies
    # in Development Phase - these are actually Frontier setup tasks
    "Frontier Staging Dependencies Complete": "Frontier: Staging Setup",

    # QA & Testing Phase parent tasks
    "FPS QA Testing": "FPS: QA Testing",
    "Frontier UAT Testing": "Frontier: UAT Testing",
    "Frontier UAT Approval": "Frontier: UAT Approval",

    # Production Deployment parent tasks
    "IGT Production Dependencies Complete": "IGT: Production Setup",
    "Cognigy Production Dependencies Complete": "Cognigy: Production Setup",
    "CSG Production Dependencies Complete (UAT Approval)": "CSG: Production Setup",
    "Frontier Production Dependencies Complete": "Frontier: Production Setup",
    "Frontier Production Go-Live Approval (CAB)": "Frontier: CAB Approval",
    "FPS Production Deployment": "FPS: Production Deployment",
}


def apply_nomenclature_updates(client, sheet_id, column_map, sheet, dry_run=True):
    """Apply nomenclature updates to Smartsheet"""

    task_col = column_map.get('Tasks')
    if not task_col:
        print("ERROR: Could not find 'Tasks' column")
        return

    updates = []
    change_log = []

    print("\n" + "=" * 80)
    print("  NOMENCLATURE STANDARDIZATION")
    print("=" * 80)
    print(f"\n  {'Row':>4} | {'Current Name':<45} | {'New Name':<30}")
    print(f"  {'-'*4}-+-{'-'*45}-+-{'-'*30}")

    for row in sheet.rows:
        # Get current task name
        current_name = None
        for cell in row.cells:
            if cell.column_id == task_col:
                current_name = cell.value
                break

        if not current_name:
            continue

        # Check if this task needs renaming
        new_name = NOMENCLATURE_UPDATES.get(current_name)
        if not new_name:
            continue

        # Skip if already correct
        if current_name == new_name:
            print(f"  {row.row_number:>4} | {current_name[:45]:<45} | (no change)")
            continue

        print(f"  {row.row_number:>4} | {current_name[:45]:<45} | {new_name:<30}")

        # Create row update
        row_update = smartsheet.models.Row()
        row_update.id = row.id
        cell = smartsheet.models.Cell()
        cell.column_id = task_col
        cell.value = new_name
        row_update.cells.append(cell)
        updates.append(row_update)

        change_log.append({
            "row": row.row_number,
            "row_id": row.id,
            "old_name": current_name,
            "new_name": new_name
        })

    print("\n" + "=" * 80)

    if dry_run:
        print("  DRY RUN - No changes applied")
        print("=" * 80)
        print(f"\n  Total rows to update: {len(updates)}")
        print(f"  Run without --dry-run to apply these changes")
    else:
        print("  APPLYING UPDATES")
        print("=" * 80)

        if updates:
            try:
                result = client.Sheets.update_rows(sheet_id, updates)
                print(f"\n  [OK] Updated {len(updates)} task names")
            except Exception as e:
                print(f"\n  [ERROR] {e}")
                raise
        else:
            print("\n  No updates needed - all names already standardized")

    # Save change log
    change_log_file = f"nomenclature_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(change_log_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "total_changes": len(change_log),
            "changes": change_log
        }, f, indent=2)
    print(f"\n  [LOG] Change log saved to {change_log_file}")

    return change_log


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Standardize task nomenclature')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  TASK NOMENCLATURE STANDARDIZATION - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Initialize
    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")

    column_map, sheet = get_column_map(client, TASK_SHEET_ID)
    print(f"  [OK] Sheet ID: {TASK_SHEET_ID}")
    print(f"  [OK] Found {len(column_map)} columns")

    # Apply updates
    change_log = apply_nomenclature_updates(client, TASK_SHEET_ID, column_map, sheet, dry_run=args.dry_run)

    print("\n" + "=" * 80)
    print("  COMPLETE")
    print("=" * 80)

    if args.dry_run:
        print("\n  To apply changes, run: python update_nomenclature.py")

    print()


if __name__ == "__main__":
    main()
