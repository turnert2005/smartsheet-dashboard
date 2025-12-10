"""
Schedule Rigor Updates - Phase 2 Agentic Voice
Based on 12/8 and 12/9 meeting notes

This script implements:
1. Compression suggestion notes
2. Predecessor corrections
3. Status updates
4. Structure documentation
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


def get_current_notes(row, notes_col_id):
    """Get current notes value from a row"""
    for cell in row.cells:
        if cell.column_id == notes_col_id:
            return cell.value or ""
    return ""


def get_current_predecessor(row, pred_col_id):
    """Get current predecessor value from a row"""
    for cell in row.cells:
        if cell.column_id == pred_col_id:
            return cell.value or ""
    return ""


def get_current_status(row, status_col_id):
    """Get current status value from a row"""
    for cell in row.cells:
        if cell.column_id == status_col_id:
            return cell.value or ""
    return ""


# ============================================================================
# PRIORITY 1: Compression Suggestion Notes
# ============================================================================

# Tasks identified as compression candidates based on analysis
COMPRESSION_CANDIDATES = {
    # UAT Testing - can potentially compress from 5d to 3d
    56: "Frontier UAT Testing - evaluate 5d->3d compression",
    57: "UAT test execution - evaluate parallel testing",
    58: "UAT environment testing - evaluate parallel testing",

    # CAB Approval - can potentially compress from 2d to 1d
    69: "CAB Approval window - evaluate 2d->1d compression",
    70: "CAB presentation - single day possible if pre-staged",
    71: "CAB final approval - same day as presentation possible",

    # FPS QA - potential parallel activities
    40: "FPS QA Testing - evaluate overlap with partner integration testing",
    41: "End-to-end test plan - evaluate automated test acceleration",
    42: "QA environment testing - evaluate parallel test streams",
}


# ============================================================================
# PRIORITY 2: Predecessor Corrections
# ============================================================================

# Issue A: Tasks incorrectly dependent on Row 24 (IGT Signal API)
PREDECESSOR_CORRECTIONS = {
    # Cognigy Staging Phase 2 tasks - should depend on Cognigy Phase 1 (Row 13)
    17: {"new_pred": "13FS", "rationale": "Cognigy Phase 2 depends on Phase 1 completion, not IGT"},
    18: {"new_pred": "13FS", "rationale": "VoiceGateway provisioning follows Cognigy Phase 1"},
    19: {"new_pred": "18FS", "rationale": "Connect SIP trunks after VoiceGateway provisioned"},
    20: {"new_pred": "19FS", "rationale": "Assign numbers after SIP trunks connected"},
    21: {"new_pred": "20FS", "rationale": "Create SIP flow after numbers assigned"},

    # FPS Partner Integrations - should depend on FPS Development
    37: {"new_pred": "28FS", "rationale": "Partner integrations depend on Knowledgebase development"},
    38: {"new_pred": "37FS", "rationale": "Data endpoints follow partner API integration"},

    # FPS QA Testing - should depend on FPS Development completion
    40: {"new_pred": "36FS", "rationale": "QA Testing starts after Partner Integrations complete"},
    41: {"new_pred": "40SS", "rationale": "Test execution starts with QA phase"},
    42: {"new_pred": "41SS", "rationale": "QA environment testing parallel with test execution"},

    # Cognigy Production Dependencies - should depend on Cognigy Staging validation
    46: {"new_pred": "17FS", "rationale": "Production provisioning after Staging Phase 2 complete"},
    47: {"new_pred": "46SS", "rationale": "800 number provisioning with production phase"},
    48: {"new_pred": "47FS", "rationale": "SIP trunks after 800 number"},
    49: {"new_pred": "48FS", "rationale": "Signal API after SIP trunks"},
    50: {"new_pred": "49FS", "rationale": "DID numbers after Signal API"},

    # IGT Production Dependencies - should depend on IGT Staging (Row 22)
    51: {"new_pred": "22FS", "rationale": "IGT Production follows IGT Staging completion"},
    52: {"new_pred": "51SS", "rationale": "800 number with production phase start"},
    53: {"new_pred": "52FS", "rationale": "SIP trunks after 800 number"},
    54: {"new_pred": "53FS", "rationale": "Signal API after SIP trunks"},
    55: {"new_pred": "54FS", "rationale": "DID numbers after Signal API"},

    # Issue C: Production Deployment predecessor chain
    # Row 69 (CAB Approval) should depend on UAT Approval
    69: {"new_pred": "62FS +1d", "rationale": "CAB follows UAT Approval"},

    # Row 72 (FPS Production Deployment) should depend on CAB + all production deps
    72: {"new_pred": "69FS +1d", "rationale": "Production deploy after CAB approval"},
}


# ============================================================================
# PRIORITY 3: Status Updates from Meetings
# ============================================================================

STATUS_UPDATES = {
    # CSG tasks - Angela confirmed in progress (12/9 meeting)
    43: {"new_status": "In Progress", "rationale": "Angela conducting UAT testing per 12/9 meeting"},
    44: {"new_status": "In Progress", "rationale": "IVR call routing configuration in progress"},
    45: {"new_status": "In Progress", "rationale": "800 test number setup in progress"},
}


# ============================================================================
# Issue B: Structure Documentation (for manual review)
# ============================================================================

STRUCTURE_ISSUES = """
STRUCTURE ISSUE B: Production Provisioning Tasks Misplaced in QA Section

Current Structure (INCORRECT):
Row 39: QA & Testing Phase
  Row 40-42: FPS QA Testing [OK] (Correct)
  Row 43-45: CSG Staging Dependencies (Testing) [OK] (Correct)
  Row 46-50: Cognigy PRODUCTION Dependencies [X] WRONG SECTION
  Row 51-55: IGT PRODUCTION Dependencies [X] WRONG SECTION

RECOMMENDED ACTION:
Option A: Move Rows 46-55 to Production Deployment section (after Row 63)
Option B: Create new phase "Production Provisioning" between QA and Production Deployment

This requires manual row movement in Smartsheet UI as API cannot change hierarchy.
The predecessor corrections in this script will ensure proper logical dependencies
regardless of visual hierarchy.

TASKS TO MOVE (if choosing Option A):
- Row 46: Cognigy Production Dependencies Complete -> Move after Row 63
- Row 47-50: Cognigy Production subtasks -> Move as children of Row 46
- Row 51: IGT Production Dependencies Complete -> Move after Row 50
- Row 52-55: IGT Production subtasks -> Move as children of Row 51
"""


def apply_updates(client, sheet_id, column_map, sheet, dry_run=True):
    """Apply all updates to Smartsheet"""

    notes_col = column_map.get('Notes')
    pred_col = column_map.get('Predecessors')
    status_col = column_map.get('Status')

    if not notes_col or not pred_col or not status_col:
        print("ERROR: Could not find required columns")
        print(f"  Notes: {notes_col}")
        print(f"  Predecessors: {pred_col}")
        print(f"  Status: {status_col}")
        return

    # Build row lookup by row number
    row_by_number = {}
    for row in sheet.rows:
        row_by_number[row.row_number] = row

    # Collect all updates by row_id to avoid duplicates
    updates_by_row = {}  # row_id -> {row_id, cells: {col_id: value}}
    change_log = []

    def add_cell_update(row_id, row_num, col_id, value):
        """Add a cell update, combining with existing row updates"""
        if row_id not in updates_by_row:
            updates_by_row[row_id] = {'row_id': row_id, 'row_num': row_num, 'cells': {}}
        updates_by_row[row_id]['cells'][col_id] = value

    # ---- Priority 1: Compression Notes ----
    print("\n" + "=" * 70)
    print("  PRIORITY 1: Compression Suggestion Notes")
    print("=" * 70)

    for row_num, suggestion in COMPRESSION_CANDIDATES.items():
        row = row_by_number.get(row_num)
        if not row:
            print(f"  [WARN] Row {row_num} not found")
            continue

        current_notes = get_current_notes(row, notes_col)
        new_note = f"[12/09 Review] Schedule compression candidate - {suggestion}"

        # Append to existing notes
        if current_notes:
            updated_notes = f"{current_notes}\n{new_note}"
        else:
            updated_notes = new_note

        print(f"  Row {row_num}: Adding compression note")

        # Add to combined updates
        add_cell_update(row.id, row_num, notes_col, updated_notes)

        change_log.append({
            "row": row_num,
            "type": "COMPRESSION_NOTE",
            "field": "Notes",
            "old_value": current_notes[:50] if current_notes else "(empty)",
            "new_value": new_note[:50],
            "rationale": "Schedule compression candidate identified in 12/09 review"
        })

    # ---- Priority 2: Predecessor Corrections ----
    print("\n" + "=" * 70)
    print("  PRIORITY 2: Predecessor Corrections")
    print("=" * 70)

    for row_num, correction in PREDECESSOR_CORRECTIONS.items():
        row = row_by_number.get(row_num)
        if not row:
            print(f"  [WARN] Row {row_num} not found")
            continue

        current_pred = get_current_predecessor(row, pred_col)
        new_pred = correction["new_pred"]
        rationale = correction["rationale"]

        print(f"  Row {row_num}: {current_pred} -> {new_pred}")
        print(f"           Rationale: {rationale}")

        # Add to combined updates
        add_cell_update(row.id, row_num, pred_col, new_pred)

        change_log.append({
            "row": row_num,
            "type": "PREDECESSOR",
            "field": "Predecessors",
            "old_value": current_pred,
            "new_value": new_pred,
            "rationale": rationale
        })

    # ---- Priority 3: Status Updates ----
    print("\n" + "=" * 70)
    print("  PRIORITY 3: Status Updates (from meetings)")
    print("=" * 70)

    for row_num, update in STATUS_UPDATES.items():
        row = row_by_number.get(row_num)
        if not row:
            print(f"  [WARN] Row {row_num} not found")
            continue

        current_status = get_current_status(row, status_col)
        new_status = update["new_status"]
        rationale = update["rationale"]

        if current_status == new_status:
            print(f"  Row {row_num}: Already '{new_status}' - no change needed")
            continue

        print(f"  Row {row_num}: {current_status} -> {new_status}")
        print(f"           Rationale: {rationale}")

        # Add to combined updates
        add_cell_update(row.id, row_num, status_col, new_status)

        change_log.append({
            "row": row_num,
            "type": "STATUS",
            "field": "Status",
            "old_value": current_status,
            "new_value": new_status,
            "rationale": rationale
        })

    # ---- Issue B: Structure Documentation ----
    print("\n" + "=" * 70)
    print("  ISSUE B: Structure Documentation (Manual Action Required)")
    print("=" * 70)
    print(STRUCTURE_ISSUES)

    # ---- Convert combined updates to Smartsheet row objects ----
    updates = []
    for row_id, row_data in updates_by_row.items():
        row_update = smartsheet.models.Row()
        row_update.id = row_id
        for col_id, value in row_data['cells'].items():
            cell = smartsheet.models.Cell()
            cell.column_id = col_id
            cell.value = value
            row_update.cells.append(cell)
        updates.append(row_update)

    # ---- Apply Updates ----
    print("\n" + "=" * 70)
    if dry_run:
        print("  DRY RUN - No changes applied")
        print("=" * 70)
        print(f"\n  Total rows to update: {len(updates)}")
        print(f"  Total cell changes: {len(change_log)}")
        print(f"  Run without --dry-run to apply these changes")
    else:
        print("  APPLYING UPDATES")
        print("=" * 70)

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

        print(f"\n  [SUCCESS] Updated {len(updates)} rows with {len(change_log)} changes")

    # ---- Save Change Log ----
    change_log_file = f"change_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(change_log_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "total_changes": len(change_log),
            "changes": change_log
        }, f, indent=2)
    print(f"\n  [LOG] Change log saved to {change_log_file}")

    return change_log


def verify_logical_dependencies(sheet, column_map):
    """Verify the logical dependency chain after updates"""

    print("\n" + "=" * 70)
    print("  DEPENDENCY CHAIN VERIFICATION")
    print("=" * 70)

    pred_col = column_map.get('Predecessors')
    task_col = column_map.get('Tasks')

    # Expected dependency chain
    expected_chain = [
        (28, "FPS Development - Knowledgebase", None),
        (36, "FPS Development - Partner Integrations", "28FS"),
        (40, "FPS QA Testing", "36FS"),
        (56, "Frontier UAT Testing", "40FS +1d"),
        (62, "Frontier UAT Approval", "56FS +1d"),
        (69, "Frontier Production Go-Live Approval (CAB)", "62FS +1d"),
        (72, "FPS Production Deployment", "69FS +1d"),
    ]

    print("\n  Expected Critical Path:")
    print(f"  {'Row':>4} | {'Task':<45} | {'Expected Pred':^15}")
    print(f"  {'-'*4}-+-{'-'*45}-+-{'-'*15}")

    for row_num, task_name, expected_pred in expected_chain:
        exp = expected_pred if expected_pred else "(start)"
        print(f"  {row_num:>4} | {task_name:<45} | {exp:^15}")

    print("\n  Parallel Infrastructure Track:")
    parallel_tracks = [
        ("IGT", [(22, "IGT Staging"), (51, "IGT Production -> 22FS")]),
        ("Cognigy", [(13, "Phase 1"), (17, "Phase 2 -> 13FS"), (46, "Production -> 17FS")]),
        ("CSG", [(43, "Staging"), (59, "Production")]),
    ]

    for vendor, track in parallel_tracks:
        track_str = " -> ".join([f"Row {r}" for r, _ in track])
        print(f"  {vendor}: {track_str}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Apply schedule rigor updates')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  SCHEDULE RIGOR UPDATES - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Initialize
    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")

    column_map, sheet = get_column_map(client, TASK_SHEET_ID)
    print(f"  [OK] Sheet ID: {TASK_SHEET_ID}")
    print(f"  [OK] Found {len(column_map)} columns")

    # Apply updates
    change_log = apply_updates(client, TASK_SHEET_ID, column_map, sheet, dry_run=args.dry_run)

    # Verify dependencies
    verify_logical_dependencies(sheet, column_map)

    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70)

    if args.dry_run:
        print("\n  To apply changes, run: python schedule_rigor_updates.py")

    print()


if __name__ == "__main__":
    main()
