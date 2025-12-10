"""
Reformat Notes to Standard Convention
Convention: [DATE] [TAG] Description

Tags:
- ACTION: Requires decision/action in meeting
- CLARIFY: Needs clarification from specific owner
- DEPENDENCY: Documents a blocking relationship
- COMPRESSION: Schedule optimization candidate
- STATUS: Progress update or completion note
- INFO: Context/reference information
- RISK: Flags a schedule or delivery risk
"""

import smartsheet
import json
from datetime import datetime
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


def get_client():
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)
    return client


# Mapping of WBS to reformatted notes
NOTE_REFORMATS = {
    # FPS Review items -> CLARIFY with @owner
    "1.5.1": "[12/10] CLARIFY @Chirag: Confirm predecessor row numbers correct after WBS reorder",

    "1.5.2": "[12/09] INFO: Staging credentials only - see 3.5 for production",

    "1.6.2": "[12/09] STATUS: Complete; accuracy enhancements in progress",

    "1.7.2": "[12/10] CLARIFY @Angela: Confirm DID count for 800 test number",

    "1.8.3": "[12/10] ACTION: Signal API - confirm if same endpoint configured by IGT/Cognigy or separate integrations (see also 3.3.3, 3.4.3)",

    "1.10": "[12/10] CLARIFY @Chirag: Signal API - FPS-developed or partner integration?",

    # Signal API consolidation - reference notes
    "3.3.3": "[12/09] INFO: See 1.8.3 for Signal API clarification",
    "3.4.3": "[12/09] INFO: See 1.8.3 for Signal API clarification",

    # Compression notes - parent tasks only
    "2.1": "[12/09] COMPRESSION: Evaluate overlap with partner integrations + parallel test streams",
    "2.2": "[12/09] COMPRESSION: Evaluate 8d to 5d reduction via parallel testing",
    "3.6": "[12/09] COMPRESSION: Evaluate 4d to 2d reduction - same-day presentation + approval",

    # Dependency notes
    "3.1": "[12/09] DEPENDENCY: ARB approval required before production deployment",

    # Clarify notes
    "3.2.2": "[12/10] CLARIFY @Angela: Confirm routing % for Unknown call types",
}

# Notes to CLEAR (compression notes moved to parent)
NOTES_TO_CLEAR = [
    "2.1.1",  # Execute end-to-end test plan (QA)
    "2.1.2",  # Complete QA environment testing
    "2.2.1",  # Execute end-to-end test plan (UAT)
    "2.2.2",  # Complete UAT environment testing
    "3.6.1",  # Present deployment plan to CAB
    "3.6.2",  # Secure Go-Live approval
]


def reformat_notes(client, sheet_id, dry_run=True):
    """Reformat all notes to standard convention"""

    sheet = client.Sheets.get_sheet(sheet_id)
    col_map = {col.title: col.id for col in sheet.columns}

    wbs_col = col_map.get('WBS')
    notes_col = col_map.get('Notes')
    task_col = col_map.get('Tasks')

    # Build WBS to row mapping
    wbs_to_row = {}
    for row in sheet.rows:
        wbs = task = notes = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value
            elif cell.column_id == notes_col:
                notes = cell.value
        if wbs:
            wbs_to_row[wbs] = {
                'row_id': row.id,
                'row_number': row.row_number,
                'task': task,
                'current_notes': notes
            }

    print("\n" + "=" * 90)
    print("  REFORMATTING NOTES TO STANDARD CONVENTION")
    print("=" * 90)
    print("\n  Convention: [DATE] [TAG] Description")
    print("  Tags: ACTION, CLARIFY, DEPENDENCY, COMPRESSION, STATUS, INFO, RISK")

    updates = []
    change_log = []

    # Apply reformatted notes
    print("\n  REFORMATTED NOTES:")
    print("  " + "-" * 85)

    for wbs, new_note in NOTE_REFORMATS.items():
        if wbs not in wbs_to_row:
            print(f"  [SKIP] {wbs}: WBS not found")
            continue

        row_info = wbs_to_row[wbs]
        old_note = row_info['current_notes'] or "(empty)"

        print(f"\n  {wbs} - {row_info['task'][:40] if row_info['task'] else '(no task)'}")
        print(f"    OLD: {old_note[:60]}...")
        print(f"    NEW: {new_note}")

        row_update = smartsheet.models.Row()
        row_update.id = row_info['row_id']
        cell = smartsheet.models.Cell()
        cell.column_id = notes_col
        cell.value = new_note
        row_update.cells.append(cell)
        updates.append(row_update)

        change_log.append({
            'wbs': wbs,
            'task': row_info['task'],
            'old_note': old_note,
            'new_note': new_note,
            'action': 'reformat'
        })

    # Clear compression notes from child tasks
    print("\n\n  CLEARING REDUNDANT CHILD NOTES:")
    print("  " + "-" * 85)

    for wbs in NOTES_TO_CLEAR:
        if wbs not in wbs_to_row:
            print(f"  [SKIP] {wbs}: WBS not found")
            continue

        row_info = wbs_to_row[wbs]
        old_note = row_info['current_notes']

        if old_note:
            print(f"  {wbs}: Clearing - '{old_note[:50]}...'")

            row_update = smartsheet.models.Row()
            row_update.id = row_info['row_id']
            cell = smartsheet.models.Cell()
            cell.column_id = notes_col
            cell.value = ""  # Clear the note
            row_update.cells.append(cell)
            updates.append(row_update)

            change_log.append({
                'wbs': wbs,
                'task': row_info['task'],
                'old_note': old_note,
                'new_note': "(cleared)",
                'action': 'clear'
            })
        else:
            print(f"  {wbs}: Already empty")

    # Apply updates
    print("\n" + "=" * 90)

    if dry_run:
        print("  DRY RUN - No changes applied")
        print("=" * 90)
        print(f"\n  Total updates: {len(updates)}")
        print(f"  Run without --dry-run to apply")
    else:
        print("  APPLYING UPDATES")
        print("=" * 90)

        if updates:
            # Apply in batches
            batch_size = 50
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                result = client.Sheets.update_rows(sheet_id, batch)
                print(f"  Updated batch {i//batch_size + 1}: {len(batch)} rows")

            print(f"\n  [OK] Applied {len(updates)} note updates")
        else:
            print("\n  No updates needed")

    return change_log


def show_final_notes(client, sheet_id):
    """Show all notes after reformatting"""

    sheet = client.Sheets.get_sheet(sheet_id)
    col_map = {col.title: col.id for col in sheet.columns}

    wbs_col = col_map.get('WBS')
    notes_col = col_map.get('Notes')
    task_col = col_map.get('Tasks')

    print("\n" + "=" * 90)
    print("  COMPLETE NOTES LIST (After Reformatting)")
    print("=" * 90)

    all_notes = []
    meeting_items = []

    for row in sheet.rows:
        wbs = task = notes = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value
            elif cell.column_id == notes_col:
                notes = cell.value

        if wbs and notes:
            all_notes.append((wbs, task, notes))
            if '[12/10]' in notes:
                meeting_items.append((wbs, task, notes))

    print(f"\n  {'WBS':<8} | {'Task':<35} | {'Note':<40}")
    print("  " + "-" * 90)

    for wbs, task, notes in all_notes:
        task_str = task[:35] if task else "(no task)"
        notes_str = notes[:40] if len(notes) <= 40 else notes[:37] + "..."
        print(f"  {wbs:<8} | {task_str:<35} | {notes_str:<40}")

    print(f"\n  Total rows with notes: {len(all_notes)}")

    # Meeting agenda items
    print("\n" + "=" * 90)
    print("  12/10 MEETING AGENDA ITEMS")
    print("=" * 90)

    for i, (wbs, task, notes) in enumerate(meeting_items, 1):
        # Extract tag
        tag = "ACTION" if "ACTION" in notes else "CLARIFY" if "CLARIFY" in notes else "OTHER"
        print(f"\n  {i}. [{tag}] {wbs} - {task[:40] if task else ''}")
        print(f"     {notes}")

    print(f"\n  Total 12/10 items: {len(meeting_items)}")

    return all_notes, meeting_items


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Reformat notes to standard convention')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()

    print("\n" + "=" * 90)
    print("  NOTES REFORMATTING - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)

    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")

    # Reformat notes
    change_log = reformat_notes(client, TASK_SHEET_ID, dry_run=args.dry_run)

    # Show final state if not dry run
    if not args.dry_run:
        all_notes, meeting_items = show_final_notes(client, TASK_SHEET_ID)

        # Save change log
        log_file = f"notes_reformat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'changes': change_log,
                'total_notes': len(all_notes),
                'meeting_items': len(meeting_items)
            }, f, indent=2)
        print(f"\n  [LOG] Saved to {log_file}")

    print("\n" + "=" * 90)
    print("  COMPLETE")
    print("=" * 90)
    print()


if __name__ == "__main__":
    main()
