"""
Comprehensive Audit and Fixes - Phase 2 Agentic Voice
December 9, 2025

Issues Identified:
1. Notes audit - current vs needed
2. Items for 12/10 meeting clarification
3. Comment/tagging recommendations
4. Update request recommendations (Chirag, Hemant)
5. Task ordering/duplication/consistency
"""

import smartsheet
import json
from datetime import datetime
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


def get_client():
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)
    return client


def audit_notes(sheet, col_map):
    """Audit current notes vs recommended notes"""

    wbs_col = col_map.get('WBS')
    task_col = col_map.get('Tasks')
    notes_col = col_map.get('Notes')

    print("\n" + "=" * 90)
    print("  1. NOTES AUDIT")
    print("=" * 90)

    current_notes = {}
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
            current_notes[wbs] = {'task': task, 'notes': notes}

    print(f"\n  Current notes count: {len(current_notes)}")

    # Notes we should have
    recommended_notes = {
        # FPS Review items (already added)
        "1.5.1": "FPS REVIEW: Confirm predecessor row numbers are correct after reorder",
        "1.5.2": "STAGING CREDENTIALS ONLY - Production credentials provisioned in 3.5",
        "1.7.2": "FPS REVIEW: Confirm DID count for 800 test number",
        "1.10": "FPS REVIEW: Clarify Signal API ownership - FPS or partner?",

        # IGT delay (should exist)
        "1.8.3": "12/05 - IGT config will take 2-3 weeks (SIP trunk delay)",

        # Compression candidates (already added via schedule_rigor_updates)
        "2.1": "Schedule compression candidate",
        "2.2": "Schedule compression candidate",
        "3.6": "Schedule compression candidate",

        # Missing - should add
        "1.1": "COMPLETE - Draft proposal submitted",
        "1.2": "COMPLETE - SOW finalized",
        "1.3": "COMPLETE - SOW approved",
        "3.1": "DEPENDENCY: Requires ARB approval before production deployment",
        "3.2.2": "Routing % for Unknown calls - confirm with CSG (Angela)",
    }

    missing_notes = []
    for wbs, note in recommended_notes.items():
        if wbs not in current_notes:
            missing_notes.append((wbs, note))
            print(f"  [MISSING] {wbs}: Should have note - '{note[:50]}...'")

    print(f"\n  Missing recommended notes: {len(missing_notes)}")
    return missing_notes


def identify_meeting_flags(sheet, col_map):
    """Identify items to flag for 12/10 meeting"""

    print("\n" + "=" * 90)
    print("  2. ITEMS FOR 12/10 MEETING CLARIFICATION")
    print("=" * 90)

    meeting_items = [
        {
            "wbs": "1.5.1",
            "topic": "VoiceGateway Prerequisites",
            "question": "Confirm predecessor dependencies are correct after WBS reorder",
            "owner": "FPS (Chirag)",
            "priority": "HIGH"
        },
        {
            "wbs": "1.7.2",
            "topic": "800 Test Number DID Count",
            "question": "How many DIDs are required for staging test number?",
            "owner": "CSG (Angela)",
            "priority": "MEDIUM"
        },
        {
            "wbs": "1.10",
            "topic": "Signal API Ownership",
            "question": "Is Signal API developed by FPS or is it a partner integration?",
            "owner": "FPS (Chirag)",
            "priority": "HIGH"
        },
        {
            "wbs": "1.8",
            "topic": "IGT SIP Trunk Status",
            "question": "Confirm Dec 23 target still achievable - any blockers?",
            "owner": "IGT (Sandeep)",
            "priority": "CRITICAL"
        },
        {
            "wbs": "3.2.2",
            "topic": "Unknown Call Routing %",
            "question": "What percentage routing for Unknown call types?",
            "owner": "CSG (Angela)",
            "priority": "MEDIUM"
        },
        {
            "wbs": "2.1/2.2",
            "topic": "QA/UAT Compression",
            "question": "Can we overlap QA and UAT or compress durations?",
            "owner": "FPS/Frontier",
            "priority": "HIGH - Schedule Recovery"
        },
        {
            "wbs": "1.9.1 vs 1.5.1",
            "topic": "VoiceGateway Sequence",
            "question": "1.5.1 activates licenses but 1.9.1 provisions - is sequence correct?",
            "owner": "Cognigy/FPS",
            "priority": "HIGH"
        }
    ]

    for item in meeting_items:
        print(f"\n  [{item['priority']}] {item['wbs']} - {item['topic']}")
        print(f"    Question: {item['question']}")
        print(f"    Owner: {item['owner']}")

    return meeting_items


def identify_duplicate_tasks(sheet, col_map):
    """Identify duplicate task names that need clarification"""

    print("\n" + "=" * 90)
    print("  3. DUPLICATE TASK NAMES REQUIRING CLARIFICATION")
    print("=" * 90)

    wbs_col = col_map.get('WBS')
    task_col = col_map.get('Tasks')

    task_names = {}
    for row in sheet.rows:
        wbs = task = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value
        if task and wbs:
            if task not in task_names:
                task_names[task] = []
            task_names[task].append(wbs)

    duplicates = {k: v for k, v in task_names.items() if len(v) > 1}

    clarifications = []
    for name, wbs_list in duplicates.items():
        print(f"\n  '{name}'")
        print(f"    Found in: {', '.join(wbs_list)}")

        # Suggest clarifications
        if "Configure IVR routing" in name:
            clarifications.append({
                "task": name,
                "wbs_list": wbs_list,
                "suggestion": "Add (Staging) and (Production) suffix"
            })
            print(f"    [FIX] Add (Staging) to 1.7.1, (Production) to 3.2.1")
        elif "Configure the Signal API" in name:
            clarifications.append({
                "task": name,
                "wbs_list": wbs_list,
                "suggestion": "Clarify vendor context - IGT vs Cognigy"
            })
            print(f"    [FIX] Clarify: Is this same Signal API across vendors?")
        elif "Execute end-to-end test plan" in name:
            clarifications.append({
                "task": name,
                "wbs_list": wbs_list,
                "suggestion": "Add (QA) and (UAT) suffix"
            })
            print(f"    [FIX] Add (QA) to 2.1.1, (UAT) to 2.2.1")
        elif "Provision 2 DID test numbers" in name:
            clarifications.append({
                "task": name,
                "wbs_list": wbs_list,
                "suggestion": "Already has vendor context from parent"
            })
            print(f"    [OK] Parent tasks differentiate (Cognigy vs IGT)")

    return clarifications


def recommend_comments_and_tags(sheet, col_map):
    """Recommend row comments and @mentions"""

    print("\n" + "=" * 90)
    print("  4. RECOMMENDED COMMENTS AND @MENTIONS")
    print("=" * 90)

    comments_to_add = [
        {
            "wbs": "1.8",
            "comment": "@Sandeep - Please confirm Dec 23 completion date for SIP trunk configuration. This is on critical path.",
            "tag": "sandeep (IGT)"
        },
        {
            "wbs": "1.10",
            "comment": "@Chirag - Clarification needed: Is Signal API FPS-owned or partner integration?",
            "tag": "Chirag Handa (FPS)"
        },
        {
            "wbs": "2.1",
            "comment": "@Hemant - QA test plan needs review. Can we compress from 5 days to 3 days?",
            "tag": "Hemant Modi (FPS)"
        },
        {
            "wbs": "3.1",
            "comment": "@Frontier - ARB meeting scheduled? This gates production deployment.",
            "tag": "Frontier"
        }
    ]

    for rec in comments_to_add:
        print(f"\n  {rec['wbs']}:")
        print(f"    Comment: {rec['comment']}")
        print(f"    Tag: {rec['tag']}")

    return comments_to_add


def recommend_update_requests():
    """Recommend update requests for Chirag and Hemant"""

    print("\n" + "=" * 90)
    print("  5. RECOMMENDED UPDATE REQUESTS")
    print("=" * 90)

    update_requests = [
        {
            "recipient": "Chirag Handa (chirag.handa@fpsinc.com)",
            "subject": "Phase 2 Agentic Voice - FPS Task Status Update",
            "rows": [
                "1.6 - FPS: Knowledgebase Development",
                "1.10 - FPS: Partner Integrations Development",
                "2.1 - FPS: QA Testing (schedule compression opportunity)",
            ],
            "message": "Please update status and confirm end dates. Specifically:\n" +
                       "1. Is 1.10 Signal API FPS-owned or partner?\n" +
                       "2. Can QA testing be compressed from 5 to 3 days?"
        },
        {
            "recipient": "Hemant Modi (hemant.modi@fpsinc.com)",
            "subject": "Phase 2 Agentic Voice - Development Status Check",
            "rows": [
                "1.6.1 - Validate KnowledgeOwl API",
                "1.6.2 - Optimize FAQ lookup for voice",
                "1.6.3 - Implement query fallback logic",
                "1.6.4 - Tune LLM responses",
            ],
            "message": "Please confirm completion status. Notes show 1.6.2 complete but accuracy enhancements in progress."
        }
    ]

    for ur in update_requests:
        print(f"\n  TO: {ur['recipient']}")
        print(f"  Subject: {ur['subject']}")
        print(f"  Rows to update:")
        for row in ur['rows']:
            print(f"    - {row}")
        print(f"  Message: {ur['message'][:80]}...")

    return update_requests


def fix_status_issues(client, sheet_id, sheet, col_map, dry_run=True):
    """Fix status inconsistencies"""

    print("\n" + "=" * 90)
    print("  6. STATUS FIXES")
    print("=" * 90)

    wbs_col = col_map.get('WBS')
    status_col = col_map.get('Status')
    end_col = col_map.get('End Date')

    # Status fixes needed
    status_fixes = {
        # Phase headers shouldn't be "Complete" if children aren't done
        "1.0": "In Progress",  # Development Phase - end Jan 7, not complete
        # These have future end dates but marked complete - likely errors
        # "1.9.1": Keep as Complete if Cognigy confirmed done
    }

    updates = []
    for row in sheet.rows:
        wbs = status = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == status_col:
                status = cell.value

        if wbs in status_fixes and status != status_fixes[wbs]:
            print(f"  {wbs}: '{status}' -> '{status_fixes[wbs]}'")

            row_update = smartsheet.models.Row()
            row_update.id = row.id
            cell = smartsheet.models.Cell()
            cell.column_id = status_col
            cell.value = status_fixes[wbs]
            row_update.cells.append(cell)
            updates.append(row_update)

    if updates and not dry_run:
        result = client.Sheets.update_rows(sheet_id, updates)
        print(f"\n  [OK] Applied {len(updates)} status fixes")
    elif updates:
        print(f"\n  [DRY RUN] Would apply {len(updates)} status fixes")
    else:
        print("\n  No status fixes needed")

    return updates


def fix_duplicate_names(client, sheet_id, sheet, col_map, dry_run=True):
    """Fix duplicate task names with clarifying context"""

    print("\n" + "=" * 90)
    print("  7. DUPLICATE NAME FIXES")
    print("=" * 90)

    wbs_col = col_map.get('WBS')
    task_col = col_map.get('Tasks')

    # Specific renames for clarity
    name_fixes = {
        "1.7.1": ("Configure IVR routing (SIP REFER)", "Configure IVR routing (SIP REFER) - Staging"),
        "3.2.1": ("Configure IVR routing (SIP REFER)", "Configure IVR routing (SIP REFER) - Production"),
        "2.1.1": ("Execute end-to-end test plan", "Execute end-to-end test plan (QA)"),
        "2.2.1": ("Execute end-to-end test plan", "Execute end-to-end test plan (UAT)"),
    }

    updates = []
    for row in sheet.rows:
        wbs = task = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value

        if wbs in name_fixes:
            old_name, new_name = name_fixes[wbs]
            if task == old_name:  # Only fix if current name matches expected
                print(f"  {wbs}: '{old_name[:40]}' -> '{new_name}'")

                row_update = smartsheet.models.Row()
                row_update.id = row.id
                cell = smartsheet.models.Cell()
                cell.column_id = task_col
                cell.value = new_name
                row_update.cells.append(cell)
                updates.append(row_update)

    if updates and not dry_run:
        result = client.Sheets.update_rows(sheet_id, updates)
        print(f"\n  [OK] Applied {len(updates)} name fixes")
    elif updates:
        print(f"\n  [DRY RUN] Would apply {len(updates)} name fixes")
    else:
        print("\n  No name fixes needed (may already be fixed)")

    return updates


def add_missing_notes(client, sheet_id, sheet, col_map, dry_run=True):
    """Add missing recommended notes"""

    print("\n" + "=" * 90)
    print("  8. ADD MISSING NOTES")
    print("=" * 90)

    wbs_col = col_map.get('WBS')
    notes_col = col_map.get('Notes')

    # Get current notes to avoid overwriting
    current_notes = {}
    row_by_wbs = {}
    for row in sheet.rows:
        wbs = notes = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == notes_col:
                notes = cell.value
        if wbs:
            current_notes[wbs] = notes
            row_by_wbs[wbs] = row

    # Notes to add (only if not already present)
    notes_to_add = {
        "3.1": "DEPENDENCY: ARB approval required before production deployment can begin",
        "3.2.2": "CLARIFY: Confirm routing % for Unknown call types with CSG (Angela)",
    }

    updates = []
    for wbs, note in notes_to_add.items():
        if wbs in row_by_wbs and not current_notes.get(wbs):
            print(f"  {wbs}: Adding note - '{note[:50]}...'")

            row_update = smartsheet.models.Row()
            row_update.id = row_by_wbs[wbs].id
            cell = smartsheet.models.Cell()
            cell.column_id = notes_col
            cell.value = note
            row_update.cells.append(cell)
            updates.append(row_update)

    if updates and not dry_run:
        result = client.Sheets.update_rows(sheet_id, updates)
        print(f"\n  [OK] Added {len(updates)} notes")
    elif updates:
        print(f"\n  [DRY RUN] Would add {len(updates)} notes")
    else:
        print("\n  No notes to add (may already exist)")

    return updates


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Comprehensive audit and fixes')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--fix', action='store_true', help='Apply fixes')
    args = parser.parse_args()

    print("\n" + "=" * 90)
    print("  COMPREHENSIVE AUDIT - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)

    client = get_client()
    sheet = client.Sheets.get_sheet(TASK_SHEET_ID)
    col_map = {col.title: col.id for col in sheet.columns}

    print(f"\n  [OK] Connected to Smartsheet")
    print(f"  [OK] Loaded {len(sheet.rows)} rows")

    # Run audits
    missing_notes = audit_notes(sheet, col_map)
    meeting_items = identify_meeting_flags(sheet, col_map)
    duplicates = identify_duplicate_tasks(sheet, col_map)
    comments = recommend_comments_and_tags(sheet, col_map)
    update_requests = recommend_update_requests()

    # Apply fixes if requested
    if args.fix:
        print("\n" + "=" * 90)
        print("  APPLYING FIXES")
        print("=" * 90)

        fix_status_issues(client, TASK_SHEET_ID, sheet, col_map, dry_run=args.dry_run)
        fix_duplicate_names(client, TASK_SHEET_ID, sheet, col_map, dry_run=args.dry_run)
        add_missing_notes(client, TASK_SHEET_ID, sheet, col_map, dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 90)
    print("  AUDIT SUMMARY")
    print("=" * 90)
    print(f"\n  Notes: {len(missing_notes)} missing recommended notes")
    print(f"  Meeting Items: {len(meeting_items)} items for 12/10 clarification")
    print(f"  Duplicates: {len(duplicates)} duplicate task names")
    print(f"  Comments: {len(comments)} recommended @mentions")
    print(f"  Update Requests: {len(update_requests)} recommended")

    # Save audit report
    report = {
        "timestamp": datetime.now().isoformat(),
        "missing_notes": missing_notes,
        "meeting_items": meeting_items,
        "duplicate_tasks": duplicates,
        "recommended_comments": comments,
        "recommended_update_requests": update_requests
    }

    report_file = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  [LOG] Audit report saved to {report_file}")

    print("\n" + "=" * 90)
    print("  COMPLETE")
    print("=" * 90)

    if not args.fix:
        print("\n  To apply fixes, run: python comprehensive_audit.py --fix")
        print("  To preview fixes, run: python comprehensive_audit.py --fix --dry-run")

    print()


if __name__ == "__main__":
    main()
