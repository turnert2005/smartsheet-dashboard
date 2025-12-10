"""
Decision Framework Execution - Phase 2 Agentic Voice
Applies all Category 1-5 fixes based on audit findings

Categories:
1. Naming standardization (Azure STT/TTS, 800 number clarification)
2. Add unambiguous predecessors
3. Rename 1.5.1 to clarify VoiceGateway prerequisites
4. Add vendor clarification to duplicate tasks (3.3.x/3.4.x)
5. Add note to 1.5.2 about staging vs production credentials
+ Flag items for FPS review
"""

import smartsheet
import json
from datetime import datetime
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


def get_client():
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)
    return client


def get_sheet_data(client, sheet_id):
    sheet = client.Sheets.get_sheet(sheet_id)
    col_map = {col.title: col.id for col in sheet.columns}

    # Build WBS to row mapping
    wbs_col = col_map.get('WBS')
    task_col = col_map.get('Tasks')

    wbs_to_row = {}
    for row in sheet.rows:
        wbs = task = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value
        if wbs:
            wbs_to_row[wbs] = {
                'row_id': row.id,
                'row_number': row.row_number,
                'task': task
            }

    return sheet, col_map, wbs_to_row


def apply_category_1_naming(client, sheet_id, col_map, wbs_to_row):
    """Category 1: Naming standardization"""
    print("\n" + "=" * 80)
    print("  CATEGORY 1: NAMING STANDARDIZATION")
    print("=" * 80)

    task_col = col_map.get('Tasks')
    updates = []

    # Azure STT/TTS separation - check 3.5.1 and 3.5.2
    naming_fixes = {
        # If these exist and need clarification
        "Provision Production Azure AI Speech STT keys": "Provision Azure Speech-to-Text (STT) keys",
        "Provision Production Azure AI Speech TTS keys": "Provision Azure Text-to-Speech (TTS) keys",
        # 800 number clarification - staging vs production
        "Set up 800 test number": "Set up 800 test number (Staging)",
        "Provision 800 number": "Provision 800 number (Production)",
        "Provision the Production 800 number": "Provision 800 number (Production)",
        "Provision the 800 number for production": "Provision 800 number (Production - IGT)",
    }

    sheet = client.Sheets.get_sheet(sheet_id)

    for row in sheet.rows:
        task = None
        for cell in row.cells:
            if cell.column_id == task_col:
                task = cell.value
                break

        if task in naming_fixes:
            new_name = naming_fixes[task]
            print(f"  [FIX] Row {row.row_number}: '{task[:40]}' -> '{new_name}'")

            row_update = smartsheet.models.Row()
            row_update.id = row.id
            cell = smartsheet.models.Cell()
            cell.column_id = task_col
            cell.value = new_name
            row_update.cells.append(cell)
            updates.append(row_update)

    if updates:
        result = client.Sheets.update_rows(sheet_id, updates)
        print(f"\n  [OK] Applied {len(updates)} naming fixes")
    else:
        print("\n  [OK] No naming fixes needed")

    return len(updates)


def apply_category_2_predecessors(client, sheet_id, col_map, wbs_to_row):
    """Category 2: Add unambiguous predecessors"""
    print("\n" + "=" * 80)
    print("  CATEGORY 2: ADD UNAMBIGUOUS PREDECESSORS")
    print("=" * 80)

    pred_col = col_map.get('Predecessors')
    if not pred_col:
        print("  [ERROR] Predecessors column not found")
        return 0

    # Predecessor assignments: target_wbs -> predecessor_wbs with relationship
    predecessor_fixes = {
        "1.4": ("1.3", "FS"),   # Frontier Staging Setup depends on SOW Approval
        "1.5": ("1.4", "FS"),   # Cognigy Phase 1 depends on Frontier Staging
        "1.6": ("1.4", "FS"),   # Knowledgebase depends on Frontier Staging
        "1.8": ("1.3", "FS"),   # IGT Staging depends on SOW Approval
        "3.2": ("2.3", "FS"),   # CSG Production depends on UAT Approval
    }

    updates = []

    for target_wbs, (pred_wbs, rel_type) in predecessor_fixes.items():
        target = wbs_to_row.get(target_wbs)
        pred = wbs_to_row.get(pred_wbs)

        if not target:
            print(f"  [SKIP] Target WBS {target_wbs} not found")
            continue
        if not pred:
            print(f"  [SKIP] Predecessor WBS {pred_wbs} not found")
            continue

        # Use row number for predecessor reference
        pred_value = f"{pred['row_number']}{rel_type}"

        print(f"  [FIX] {target_wbs} '{target['task'][:30]}' <- {pred_wbs} ({pred_value})")

        row_update = smartsheet.models.Row()
        row_update.id = target['row_id']
        cell = smartsheet.models.Cell()
        cell.column_id = pred_col
        cell.value = pred_value
        row_update.cells.append(cell)
        updates.append(row_update)

    if updates:
        result = client.Sheets.update_rows(sheet_id, updates)
        print(f"\n  [OK] Applied {len(updates)} predecessor fixes")
    else:
        print("\n  [OK] No predecessor fixes needed")

    return len(updates)


def apply_category_3_rename(client, sheet_id, col_map, wbs_to_row):
    """Category 3: Rename 1.5.1 to clarify VoiceGateway prerequisites"""
    print("\n" + "=" * 80)
    print("  CATEGORY 3: RENAME 1.5.1 (VOICEGATEWAY PREREQUISITES)")
    print("=" * 80)

    task_col = col_map.get('Tasks')
    target = wbs_to_row.get("1.5.1")

    if not target:
        print("  [SKIP] WBS 1.5.1 not found")
        return 0

    new_name = "Validate VoiceGateway license prerequisites"
    print(f"  [FIX] 1.5.1: '{target['task']}' -> '{new_name}'")

    row_update = smartsheet.models.Row()
    row_update.id = target['row_id']
    cell = smartsheet.models.Cell()
    cell.column_id = task_col
    cell.value = new_name
    row_update.cells.append(cell)

    result = client.Sheets.update_rows(sheet_id, [row_update])
    print(f"\n  [OK] Renamed 1.5.1")

    return 1


def apply_category_4_vendor_clarification(client, sheet_id, col_map, wbs_to_row):
    """Category 4: Add vendor clarification to duplicate tasks (3.3.x/3.4.x)"""
    print("\n" + "=" * 80)
    print("  CATEGORY 4: ADD VENDOR CLARIFICATION (3.3.x/3.4.x)")
    print("=" * 80)

    task_col = col_map.get('Tasks')

    # Vendor clarifications for potentially duplicate tasks
    vendor_clarifications = {
        # Cognigy Production Setup tasks (3.3.x)
        "3.3.1": ("Provision 800 number", "Provision 800 number (Cognigy)"),
        "3.3.2": ("Set up SIP trunks", "Set up SIP trunks (to Cognigy)"),
        # IGT Production Setup tasks (3.4.x)
        "3.4.1": ("Provision 800 number", "Provision 800 number (IGT)"),
    }

    updates = []

    for wbs, (current_pattern, new_name) in vendor_clarifications.items():
        target = wbs_to_row.get(wbs)
        if not target:
            print(f"  [SKIP] WBS {wbs} not found")
            continue

        # Only update if it matches the pattern (might already be fixed)
        if target['task'] and current_pattern in target['task']:
            print(f"  [FIX] {wbs}: '{target['task']}' -> '{new_name}'")

            row_update = smartsheet.models.Row()
            row_update.id = target['row_id']
            cell = smartsheet.models.Cell()
            cell.column_id = task_col
            cell.value = new_name
            row_update.cells.append(cell)
            updates.append(row_update)
        else:
            print(f"  [OK] {wbs}: Already clarified or different - '{target['task']}'")

    if updates:
        result = client.Sheets.update_rows(sheet_id, updates)
        print(f"\n  [OK] Applied {len(updates)} vendor clarifications")
    else:
        print("\n  [OK] No vendor clarifications needed")

    return len(updates)


def apply_category_5_notes(client, sheet_id, col_map, wbs_to_row):
    """Category 5: Add note to 1.5.2 about staging vs production credentials"""
    print("\n" + "=" * 80)
    print("  CATEGORY 5: ADD CLARIFICATION NOTES")
    print("=" * 80)

    comments_col = col_map.get('Comments') or col_map.get('Notes')

    if not comments_col:
        print("  [WARN] No Comments/Notes column found - will add to task name")
        # Fall back to appending to task name
        task_col = col_map.get('Tasks')
        target = wbs_to_row.get("1.5.2")

        if target and target['task']:
            if "STAGING ONLY" not in target['task']:
                new_name = f"{target['task']} [STAGING ONLY - Production creds in 3.5]"
                print(f"  [FIX] 1.5.2: Adding staging clarification")

                row_update = smartsheet.models.Row()
                row_update.id = target['row_id']
                cell = smartsheet.models.Cell()
                cell.column_id = task_col
                cell.value = new_name
                row_update.cells.append(cell)

                result = client.Sheets.update_rows(sheet_id, [row_update])
                print(f"  [OK] Added clarification to 1.5.2")
                return 1
        return 0

    # Add note to Comments column
    target = wbs_to_row.get("1.5.2")
    if not target:
        print("  [SKIP] WBS 1.5.2 not found")
        return 0

    note = "STAGING CREDENTIALS ONLY - Production credentials provisioned in 3.5 (Frontier: Production Credentials)"
    print(f"  [FIX] 1.5.2: Adding note - '{note[:50]}...'")

    row_update = smartsheet.models.Row()
    row_update.id = target['row_id']
    cell = smartsheet.models.Cell()
    cell.column_id = comments_col
    cell.value = note
    row_update.cells.append(cell)

    result = client.Sheets.update_rows(sheet_id, [row_update])
    print(f"\n  [OK] Added clarification note to 1.5.2")

    return 1


def add_fps_review_flags(client, sheet_id, col_map, wbs_to_row):
    """Add FPS review flags for items needing clarification"""
    print("\n" + "=" * 80)
    print("  FPS REVIEW FLAGS")
    print("=" * 80)

    comments_col = col_map.get('Comments') or col_map.get('Notes')

    fps_flags = [
        ("1.5.1", "FPS REVIEW: Confirm predecessor row numbers are correct after reorder"),
        ("1.7.2", "FPS REVIEW: Confirm DID count for 800 test number"),
        ("1.10", "FPS REVIEW: Clarify Signal API ownership - FPS or partner?"),
    ]

    if not comments_col:
        print("  [WARN] No Comments column - flags will be documented in summary only")
        for wbs, flag in fps_flags:
            print(f"  [FLAG] {wbs}: {flag}")
        return 0

    updates = []
    for wbs, flag in fps_flags:
        target = wbs_to_row.get(wbs)
        if not target:
            print(f"  [SKIP] WBS {wbs} not found")
            continue

        print(f"  [FLAG] {wbs}: {flag[:50]}...")

        row_update = smartsheet.models.Row()
        row_update.id = target['row_id']
        cell = smartsheet.models.Cell()
        cell.column_id = comments_col
        cell.value = flag
        row_update.cells.append(cell)
        updates.append(row_update)

    if updates:
        result = client.Sheets.update_rows(sheet_id, updates)
        print(f"\n  [OK] Added {len(updates)} FPS review flags")

    return len(updates)


def generate_timeline_summary(client, sheet_id, col_map):
    """Generate timeline summary with critical path"""
    print("\n" + "=" * 80)
    print("  UPDATED TIMELINE SUMMARY")
    print("=" * 80)

    sheet = client.Sheets.get_sheet(sheet_id)

    wbs_col = col_map.get('WBS')
    task_col = col_map.get('Tasks')
    start_col = col_map.get('Start Date')
    end_col = col_map.get('End Date')
    pred_col = col_map.get('Predecessors')
    status_col = col_map.get('Status')

    # Collect phase summary
    phases = {
        "1.0": {"name": "Development Phase", "tasks": [], "end_date": None},
        "2.0": {"name": "QA & Testing Phase", "tasks": [], "end_date": None},
        "3.0": {"name": "Production Deployment", "tasks": [], "end_date": None},
    }

    all_tasks = []

    for row in sheet.rows:
        wbs = task = start = end = pred = status = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value
            elif cell.column_id == start_col:
                start = cell.value
            elif cell.column_id == end_col:
                end = cell.value
            elif cell.column_id == pred_col:
                pred = cell.value
            elif cell.column_id == status_col:
                status = cell.value

        if not wbs:
            continue

        all_tasks.append({
            "wbs": wbs,
            "task": task,
            "start": start,
            "end": end,
            "predecessor": pred,
            "status": status
        })

        # Track phase end dates
        phase_key = f"{wbs.split('.')[0]}.0"
        if phase_key in phases and end:
            if not phases[phase_key]["end_date"] or str(end) > str(phases[phase_key]["end_date"]):
                phases[phase_key]["end_date"] = end

    # Print phase summary
    print(f"\n  {'Phase':<30} | {'End Date':<12} | {'Status':<15}")
    print(f"  {'-'*30}-+-{'-'*12}-+-{'-'*15}")

    for phase_key, phase in phases.items():
        end_str = str(phase["end_date"])[:10] if phase["end_date"] else "(no date)"
        print(f"  {phase['name']:<30} | {end_str:<12} |")

    # Find critical path (tasks with latest end dates and sequential dependencies)
    print("\n  CRITICAL PATH TASKS:")
    print(f"  {'-'*70}")

    # Sort by end date to identify potential critical path
    dated_tasks = [t for t in all_tasks if t['end'] and t['wbs'].count('.') == 1]
    dated_tasks.sort(key=lambda x: str(x['end']), reverse=True)

    for i, task in enumerate(dated_tasks[:10]):
        end_str = str(task['end'])[:10]
        pred_str = task['predecessor'] if task['predecessor'] else "(none)"
        print(f"  {task['wbs']:<6} | {end_str} | {task['task'][:40]} | Pred: {pred_str}")

    # Calculate go-live impact
    print("\n  GO-LIVE DATE ANALYSIS:")
    print(f"  {'-'*70}")

    # Find Production Deployment end date
    prod_end = phases.get("3.0", {}).get("end_date")
    if prod_end:
        print(f"  Production Deployment Completion: {str(prod_end)[:10]}")

    return all_tasks


def main():
    print("\n" + "=" * 80)
    print("  DECISION FRAMEWORK EXECUTION - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")

    sheet, col_map, wbs_to_row = get_sheet_data(client, TASK_SHEET_ID)
    print(f"  [OK] Loaded sheet with {len(wbs_to_row)} WBS entries")

    # Print available columns
    print(f"\n  Available columns: {', '.join(col_map.keys())}")

    # Execute categories
    total_fixes = 0

    total_fixes += apply_category_1_naming(client, TASK_SHEET_ID, col_map, wbs_to_row)

    # Refresh data after naming changes
    sheet, col_map, wbs_to_row = get_sheet_data(client, TASK_SHEET_ID)

    total_fixes += apply_category_2_predecessors(client, TASK_SHEET_ID, col_map, wbs_to_row)
    total_fixes += apply_category_3_rename(client, TASK_SHEET_ID, col_map, wbs_to_row)

    # Refresh again
    sheet, col_map, wbs_to_row = get_sheet_data(client, TASK_SHEET_ID)

    total_fixes += apply_category_4_vendor_clarification(client, TASK_SHEET_ID, col_map, wbs_to_row)
    total_fixes += apply_category_5_notes(client, TASK_SHEET_ID, col_map, wbs_to_row)

    # Add FPS review flags
    add_fps_review_flags(client, TASK_SHEET_ID, col_map, wbs_to_row)

    # Generate timeline summary
    generate_timeline_summary(client, TASK_SHEET_ID, col_map)

    # Summary
    print("\n" + "=" * 80)
    print("  EXECUTION SUMMARY")
    print("=" * 80)
    print(f"\n  Total fixes applied: {total_fixes}")
    print(f"  Categories completed: 1-5")
    print(f"  FPS review flags: 3 items flagged")

    # Save execution log
    log_file = f"decision_framework_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_fixes": total_fixes,
            "categories": ["naming", "predecessors", "rename", "vendor_clarification", "notes"],
            "fps_flags": 3
        }, f, indent=2)
    print(f"  [LOG] Saved to {log_file}")

    print("\n" + "=" * 80)
    print("  COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
