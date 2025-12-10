"""
Smartsheet Schedule Update Script
Generated: 2025-12-09 17:47:36
Target: Jan 13, 2026 Baseline

This script updates the schedule with corrected baselines.
"""

import smartsheet
import os
from datetime import datetime

# Initialize client
SMARTSHEET_TOKEN = os.environ.get('SMARTSHEET_ACCESS_TOKEN')
if not SMARTSHEET_TOKEN:
    raise ValueError("Set SMARTSHEET_ACCESS_TOKEN environment variable")

client = smartsheet.Smartsheet(SMARTSHEET_TOKEN)
client.errors_as_exceptions(True)

# Sheet ID - UPDATE THIS
SHEET_ID = 0  # <-- Enter your sheet ID here

def get_column_ids():
    """Get column IDs from the sheet"""
    sheet = client.Sheets.get_sheet(SHEET_ID)

    column_map = {}
    for col in sheet.columns:
        column_map[col.title] = col.id

    print("Column IDs found:")
    for name, cid in column_map.items():
        print(f"  {name}: {cid}")

    return column_map

def update_baselines(column_map):
    """Update baseline dates"""

    baseline_finish_col = column_map.get('Baseline Finish')
    baseline_start_col = column_map.get('Baseline Start')

    if not baseline_finish_col:
        print("ERROR: Could not find 'Baseline Finish' column")
        return

    updates = []

    # Baseline updates for Jan 13 target
    baseline_updates = [
        # Row 17: Cognigy Staging Dependencies Phase 2
        {
            'row_id': 2910010229591940,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 19: Connect SIP trunks
        {
            'row_id': 552926471196548,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 20: Assign numbers
        {
            'row_id': 1282035400249220,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 21: Create SIP flow
        {
            'row_id': 6911534934462340,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 22: IGT Staging Dependencies Complete
        {
            'row_id': 7413609856962436,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 23: Configure 800 number for SIP REFER for C
        {
            'row_id': 3930626191724420,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 24: Set up SIP trunks via NICE CXone
        {
            'row_id': 6182426005409668,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 25: Configure the Signal API
        {
            'row_id': 1678826378039172,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 26: Complete queue mapping
        {
            'row_id': 7308325912252292,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 27: Provision 8 DID test numbers
        {
            'row_id': 2804726284881796,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 28: FPS Development - Knowledgebase
        {
            'row_id': 1784110322749316,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 32: Tune LLM responses for accuracy and clar
        {
            'row_id': 8434225819094916,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-14',
        },
        # Row 33: Frontier Production Dependencies Complet
        {
            'row_id': 6287709950119812,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-07',
        },
        # Row 34: Secure Architecture Review Board (ARB) a
        {
            'row_id': 7871275865673604,
            'baseline_finish': '2025-12-14',
            'baseline_start': '2025-12-07',
        },
        # Row 36: FPS Development - Partner Integrations
        {
            'row_id': 4035910136434564,
            'baseline_finish': '2025-12-18',
            'baseline_start': '2025-12-18',
        },
        # Row 37: Implement required partner API integrati
        {
            'row_id': 4493576145145732,
            'baseline_finish': '2025-12-18',
            'baseline_start': '2025-12-18',
        },
        # Row 38: Set up the necessary data exchange endpo
        {
            'row_id': 6745375958830980,
            'baseline_finish': '2025-12-18',
            'baseline_start': '2025-12-18',
        },
        # Row 39: QA & Testing Phase
        {
            'row_id': 8331586707591044,
            'baseline_finish': '2025-12-25',
            'baseline_start': '2025-12-14',
        },
        # Row 40: FPS QA Testing
        {
            'row_id': 376735439196036,
            'baseline_finish': '2025-12-18',
            'baseline_start': '2025-12-14',
        },
        # Row 41: Execute the full end-to-end Agentic Voic
        {
            'row_id': 16364796841860,
            'baseline_finish': '2025-12-18',
            'baseline_start': '2025-12-14',
        },
        # Row 42: Perform all testing within the QA enviro
        {
            'row_id': 8997175772516228,
            'baseline_finish': '2025-12-18',
            'baseline_start': '2025-12-14',
        },
        # Row 43: CSG Staging Dependencies Complete (Testi
        {
            'row_id': 4880335066566532,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 44: Configure IVR call routing using SIP REF
        {
            'row_id': 2268164610527108,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 45: Set up the 800 test number for the direc
        {
            'row_id': 4519964424212356,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 46: Cognigy Production Dependencies Complete
        {
            'row_id': 2628535252881284,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 47: Provision the Production 800 number
        {
            'row_id': 3394064517369732,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 48: Set up SIP trunks to Cognigy
        {
            'row_id': 5645864331054980,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 49: Configure the Signal API
        {
            'row_id': 1142264703684484,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 50: Provision 2 DID test numbers
        {
            'row_id': 6771764237897604,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 51: IGT Production Dependencies Complete
        {
            'row_id': 7132134880251780,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 52: Provision the 800 number for production
        {
            'row_id': 2831114563948420,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 53: Set up SIP trunks to Cognigy
        {
            'row_id': 5082914377633668,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 54: Configure the Signal API
        {
            'row_id': 579314750263172,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 55: Provision 2 DID test numbers
        {
            'row_id': 7897664144740228,
            'baseline_finish': '2025-12-21',
            'baseline_start': '2025-12-21',
        },
        # Row 56: Frontier UAT Testing
        {
            'row_id': 1502635346038660,
            'baseline_finish': '2025-12-25',
            'baseline_start': '2025-12-21',
        },
        # Row 57: Execute the full end-to-end Agentic Voic
        {
            'row_id': 1705214657105796,
            'baseline_finish': '2025-12-25',
            'baseline_start': '2025-12-21',
        },
        # Row 58: Perform all testing within the UAT envir
        {
            'row_id': 7334714191318916,
            'baseline_finish': '2025-12-25',
            'baseline_start': '2025-12-21',
        },
        # Row 59: CSG Production Dependencies Complete (UA
        {
            'row_id': 6006234973409156,
            'baseline_finish': '2025-12-23',
            'baseline_start': '2025-12-23',
        },
        # Row 60: Configure Production IVR call routing us
        {
            'row_id': 8202281348435844,
            'baseline_finish': '2025-12-23',
            'baseline_start': '2025-12-23',
        },
        # Row 61: Set the routing percentage for “Unknown”
        {
            'row_id': 883931953958788,
            'baseline_finish': '2025-12-23',
            'baseline_start': '2025-12-23',
        },
        # Row 62: Frontier UAT Approval
        {
            'row_id': 3754435159723908,
            'baseline_finish': '2025-12-25',
            'baseline_start': '2025-12-25',
        },
        # Row 63: Obtain formal UAT sign-off
        {
            'row_id': 5387531581329284,
            'baseline_finish': '2025-12-25',
            'baseline_start': '2025-12-25',
        },
        # Row 64: Production Deployment
        {
            'row_id': 8258034787094404,
            'baseline_finish': '2026-01-13',
            'baseline_start': '2025-12-28',
        },
        # Row 65: Frontier Production Dependencies Complet
        {
            'row_id': 939685392617348,
            'baseline_finish': '2026-01-11',
            'baseline_start': '2025-12-28',
        },
        # Row 66: Provision Production Azure AI Speech STT
        {
            'row_id': 3135731767644036,
            'baseline_finish': '2026-01-11',
            'baseline_start': '2025-12-28',
        },
        # Row 67: Provision Production Azure AI Speech TTS
        {
            'row_id': 7639331395014532,
            'baseline_finish': '2026-01-11',
            'baseline_start': '2025-12-28',
        },
        # Row 68: Set up Production OpenAI LLM credentials
        {
            'row_id': 2009831860801412,
            'baseline_finish': '2026-01-11',
            'baseline_start': '2025-12-28',
        },
        # Row 69: Frontier Production Go-Live Approval (CA
        {
            'row_id': 5443285019987844,
            'baseline_finish': '2026-01-12',
            'baseline_start': '2026-01-11',
        },
        # Row 70: Present the deployment plan to the Chang
        {
            'row_id': 6513431488171908,
            'baseline_finish': '2026-01-12',
            'baseline_start': '2026-01-11',
        },
        # Row 71: Secure final approval for the Production
        {
            'row_id': 4261631674486660,
            'baseline_finish': '2026-01-12',
            'baseline_start': '2026-01-11',
        },
        # Row 72: FPS Production Deployment
        {
            'row_id': 3191485206302596,
            'baseline_finish': '2026-01-13',
            'baseline_start': '2026-01-13',
        },
        # Row 73: Deploy the solution to Production
        {
            'row_id': 8765231301857156,
            'baseline_finish': '2026-01-13',
            'baseline_start': '2026-01-13',
        },
        # Row 74: Perform sanity testing to confirm core f
        {
            'row_id': 180244512182148,
            'baseline_finish': '2026-01-13',
            'baseline_start': '2026-01-13',
        },
        # Row 75: Initiate post-launch monitoring to ensur
        {
            'row_id': 4683844139552644,
            'baseline_finish': '2026-01-13',
            'baseline_start': '2026-01-13',
        },
    ]

    # Build row updates
    for update in baseline_updates:
        row = smartsheet.models.Row()
        row.id = update['row_id']

        # Baseline Finish
        row.cells.append({
            'column_id': baseline_finish_col,
            'value': update['baseline_finish']
        })

        # Baseline Start (if provided)
        if update['baseline_start'] and baseline_start_col:
            row.cells.append({
                'column_id': baseline_start_col,
                'value': update['baseline_start']
            })

        updates.append(row)

    # Apply updates in batches of 50
    print(f"Applying {len(updates)} baseline updates...")

    for i in range(0, len(updates), 50):
        batch = updates[i:i+50]
        result = client.Sheets.update_rows(SHEET_ID, batch)
        print(f"  Updated rows {i+1} to {min(i+50, len(updates))}")

    print("Baseline updates complete!")


def main():
    """Main entry point"""
    print("=" * 60)
    print("  SMARTSHEET SCHEDULE UPDATE")
    print("  Target Baseline: Jan 13, 2026")
    print("=" * 60)

    if SHEET_ID == 0:
        print("\nERROR: Please set the SHEET_ID variable in this script")
        print("You can find it in the sheet URL or properties")
        return

    column_map = get_column_ids()
    update_baselines(column_map)

    print("\n" + "=" * 60)
    print("  UPDATE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
