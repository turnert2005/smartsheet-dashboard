"""
Child Task Nomenclature Refactoring - Phase 2 Agentic Voice
Makes child task names more concise and clear

Principles:
1. Remove redundant context (parent provides context)
2. Use consistent action verbs
3. Remove unnecessary articles ("the", "a")
4. Keep technical specifics but trim verbosity
"""

import smartsheet
import json
from datetime import datetime
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


# Mapping: current_name -> new_concise_name
NOMENCLATURE_REFACTORING = {
    # 1.1 FPS Draft Proposal
    "Draft the initial proposal for the Agentic Voice project": "Draft initial proposal",
    "Submit the proposal for stakeholder review": "Submit for stakeholder review",

    # 1.2 FPS Final Proposal (SOW)
    "Finalize the Statement of Work (SOW) contract": "Finalize SOW contract",
    "Submit the SOW for signature": "Submit SOW for signature",

    # 1.3 Frontier SOW Approval
    "Obtain formal approval on the Statement of Work (SOW).": "Obtain formal SOW approval",

    # 1.4 Frontier: Staging Setup
    "Provision KnowledgeOwl APIs for the Staging environment": "Provision KnowledgeOwl APIs",
    "Generate and configure the OpenAI LLM (gpt-4o-mini) API key for Staging": "Configure OpenAI LLM API key",

    # 1.5 Cognigy: Staging Setup Phase 1 (already concise)

    # 1.6 FPS: Knowledgebase Development
    "Validate the KnowledgeOwl API": "Validate KnowledgeOwl API",
    "Optimize FAQ lookup specifically for voice interactions": "Optimize FAQ lookup for voice",
    "Implement fallback logic for unanswered or unclear queries": "Implement query fallback logic",
    "Tune LLM responses for accuracy and clarity": "Tune LLM responses",

    # 1.7 CSG: Staging Setup
    "Configure IVR call routing using SIP REFER to IGT": "Configure IVR routing (SIP REFER)",
    "Set up the 800 test number for the direct_AI English flow": "Set up 800 test number",

    # 1.8 IGT: Staging Setup
    "Configure 800 number for SIP REFER for CSG Lookup": "Configure 800 number (SIP REFER)",
    "Set up SIP trunks via NICE CXone": "Set up SIP trunks (NICE CXone)",

    # 1.9 Cognigy: Staging Setup Phase 2 (already concise)

    # 1.10 FPS: Partner Integrations Development
    "Implement required partner API integrations": "Implement partner API integrations",
    "Set up the necessary data exchange endpoints": "Set up data exchange endpoints",

    # 2.1 FPS: QA Testing
    "Execute the full end-to-end Agentic Voice test plan": "Execute end-to-end test plan",
    "Perform all testing within the QA environment": "Complete QA environment testing",

    # 2.2 Frontier: UAT Testing
    "Perform all testing within the UAT environment": "Complete UAT environment testing",

    # 2.3 Frontier: UAT Approval (already concise)

    # 3.1 Frontier: Production ARB Approval
    "Secure Architecture Review Board (ARB) approval": "Secure ARB approval",
    "Validate Production KnowledgeOwl APIs": "Validate KnowledgeOwl APIs",

    # 3.2 CSG: Production Setup
    "Configure Production IVR call routing using SIP REFER": "Configure IVR routing (SIP REFER)",
    "Set the routing percentage for �Unknown� call types": "Set Unknown call routing %",

    # 3.3 Cognigy: Production Setup
    "Provision the Production 800 number": "Provision 800 number",
    "Set up SIP trunks to Cognigy": "Set up SIP trunks",

    # 3.4 IGT: Production Setup
    "Provision the 800 number for production": "Provision 800 number",

    # 3.5 Frontier: Production Credentials
    "Provision Production Azure AI Speech STT keys": "Provision Azure Speech STT keys",
    "Provision Production Azure AI Speech TTS keys": "Provision Azure Speech TTS keys",
    "Set up Production OpenAI LLM credentials": "Set up OpenAI LLM credentials",

    # 3.6 Frontier: CAB Approval
    "Present the deployment plan to the Change Advisory Board (CAB)": "Present deployment plan to CAB",
    "Secure final approval for the Production Go-Live": "Secure Go-Live approval",

    # 3.7 FPS: Production Deployment
    "Deploy the solution to Production": "Deploy to Production",
    "Perform sanity testing to confirm core functionality": "Perform sanity testing",
    "Initiate post-launch monitoring to ensure stability and performance": "Initiate post-launch monitoring",
}


def get_client():
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)
    return client


def refactor_nomenclature(client, sheet_id, dry_run=True):
    sheet = client.Sheets.get_sheet(sheet_id)
    col_map = {col.title: col.id for col in sheet.columns}

    task_col = col_map.get('Tasks')
    wbs_col = col_map.get('WBS')

    updates = []
    change_log = []

    print("\n" + "=" * 90)
    print("  CHILD TASK NOMENCLATURE REFACTORING")
    print("=" * 90)
    print(f"\n  {'WBS':<10} | {'Current':<40} | {'New':<35}")
    print(f"  {'-'*10}-+-{'-'*40}-+-{'-'*35}")

    for row in sheet.rows:
        wbs = task = None
        for cell in row.cells:
            if cell.column_id == wbs_col:
                wbs = cell.value
            elif cell.column_id == task_col:
                task = cell.value

        if not wbs or not task:
            continue

        # Only process child tasks (X.Y.Z format)
        depth = wbs.count('.')
        if depth != 2:
            continue

        # Check if this task needs refactoring
        new_name = NOMENCLATURE_REFACTORING.get(task)
        if not new_name:
            continue

        print(f"  {wbs:<10} | {task[:40]:<40} | {new_name:<35}")

        row_update = smartsheet.models.Row()
        row_update.id = row.id
        cell = smartsheet.models.Cell()
        cell.column_id = task_col
        cell.value = new_name
        row_update.cells.append(cell)
        updates.append(row_update)

        change_log.append({
            "wbs": wbs,
            "old_name": task,
            "new_name": new_name
        })

    print("\n" + "=" * 90)

    if dry_run:
        print("  DRY RUN - No changes applied")
        print("=" * 90)
        print(f"\n  Total tasks to refactor: {len(updates)}")
        print(f"  Run without --dry-run to apply")
    else:
        print("  APPLYING CHANGES")
        print("=" * 90)

        if updates:
            batch_size = 50
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                result = client.Sheets.update_rows(sheet_id, batch)
                print(f"  Updated batch {i//batch_size + 1}: {len(batch)} tasks")

            print(f"\n  [OK] Refactored {len(updates)} task names")
        else:
            print("\n  No changes needed")

    # Save change log
    log_file = f"nomenclature_refactor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "changes": change_log
        }, f, indent=2)
    print(f"\n  [LOG] Saved to {log_file}")

    return change_log


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Refactor child task nomenclature')
    parser.add_argument('--dry-run', action='store_true', help='Preview without applying')
    args = parser.parse_args()

    print("\n" + "=" * 90)
    print("  CHILD TASK NOMENCLATURE REFACTORING - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)

    client = get_client()
    print(f"\n  [OK] Connected to Smartsheet")

    refactor_nomenclature(client, TASK_SHEET_ID, dry_run=args.dry_run)

    print("\n" + "=" * 90)
    print("  COMPLETE")
    print("=" * 90)

    if args.dry_run:
        print("\n  To apply: python refactor_child_tasks.py")
    print()


if __name__ == "__main__":
    main()
