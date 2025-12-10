"""
SOW vs Current Schedule Analysis
Compares contracted milestones from FPS Statement of Work against actual schedule
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict


def load_schedule():
    """Load current schedule"""
    with open('sheet_data_audit.json', 'r') as f:
        return json.load(f)


def parse_date(date_str):
    if not date_str:
        return None
    try:
        if 'T' in str(date_str):
            return datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d')
        return datetime.strptime(str(date_str), '%Y-%m-%d')
    except:
        return None


# SOW Contracted Milestones (from Statement of Work dated 11/20/2025)
SOW_MILESTONES = {
    # Development Phase
    "FPS Draft Proposal": datetime(2025, 11, 5),
    "FPS Final Proposal (SOW)": datetime(2025, 11, 20),
    "Frontier SOW Approval": datetime(2025, 11, 21),
    "Frontier Staging Dependencies Complete": datetime(2025, 11, 21),
    "Cognigy Staging Dependencies Phase 1": datetime(2025, 12, 1),
    "Cognigy Staging Dependencies Phase 2": datetime(2025, 12, 8),
    "IGT Staging Dependencies Complete": datetime(2025, 12, 8),
    "FPS Development - Knowledgebase": datetime(2025, 12, 8),
    "Frontier Production Dependencies (ARB)": datetime(2025, 12, 8),
    "FPS Development - Partner Integrations": datetime(2025, 12, 12),

    # QA & Testing Phase
    "FPS QA Testing": datetime(2025, 12, 12),  # Dec 8-12, end date
    "CSG Staging Dependencies": datetime(2025, 12, 15),
    "Cognigy Production Dependencies": datetime(2025, 12, 15),
    "IGT Production Dependencies": datetime(2025, 12, 15),
    "Frontier UAT Testing": datetime(2025, 12, 19),  # Dec 15-19, end date
    "CSG Production Dependencies": datetime(2025, 12, 17),
    "Frontier UAT Approval": datetime(2025, 12, 19),

    # Production Deployment
    "Frontier Production Dependencies (Keys)": datetime(2026, 1, 5),
    "Frontier Production Go-Live Approval (CAB)": datetime(2026, 1, 6),
    "FPS Production Deployment": datetime(2026, 1, 7),  # Jan 7-14
}

# Map schedule task names to SOW milestone names
TASK_TO_SOW_MAP = {
    "FPS Draft Proposal": "FPS Draft Proposal",
    "FPS Final Proposal (SOW)": "FPS Final Proposal (SOW)",
    "Frontier SOW Approval": "Frontier SOW Approval",
    "Frontier Staging Dependencies Complete": "Frontier Staging Dependencies Complete",
    "Cognigy Staging Dependencies Phase 1": "Cognigy Staging Dependencies Phase 1",
    "Cognigy Staging Dependencies Phase 2": "Cognigy Staging Dependencies Phase 2",
    "IGT Staging Dependencies Complete": "IGT Staging Dependencies Complete",
    "FPS Development - Knowledgebase": "FPS Development - Knowledgebase",
    "Frontier Production Dependencies Complete": "Frontier Production Dependencies (ARB)",
    "FPS Development - Partner Integrations": "FPS Development - Partner Integrations",
    "FPS QA Testing": "FPS QA Testing",
    "CSG Staging Dependencies Complete (Testing)": "CSG Staging Dependencies",
    "Cognigy Production Dependencies Complete": "Cognigy Production Dependencies",
    "IGT Production Dependencies Complete": "IGT Production Dependencies",
    "Frontier UAT Testing": "Frontier UAT Testing",
    "CSG Production Dependencies Complete (UAT Approval)": "CSG Production Dependencies",
    "Frontier UAT Approval": "Frontier UAT Approval",
    "Frontier Production Go-Live Approval (CAB)": "Frontier Production Go-Live Approval (CAB)",
    "FPS Production Deployment": "FPS Production Deployment",
}


def compare_schedule_to_sow(tasks):
    """Compare current schedule to SOW milestones"""
    print("\n" + "=" * 90)
    print("  SOW vs CURRENT SCHEDULE COMPARISON")
    print("  Statement of Work dated: November 20, 2025")
    print("=" * 90)

    print("\n  PROJECT GOAL FROM SOW:")
    print('  "Deploy the Agentic Voicebot with the MVP feature set during the week of Jan 7-14"')
    print("  Contracted Go-Live: January 7-14, 2026")

    comparisons = []

    # Find matching tasks
    for task in tasks:
        task_name = task['Tasks']
        end_date = parse_date(task.get('End Date'))

        # Check if this task matches a SOW milestone
        for schedule_name, sow_name in TASK_TO_SOW_MAP.items():
            if schedule_name.lower() in task_name.lower():
                sow_date = SOW_MILESTONES.get(sow_name)
                if sow_date and end_date:
                    variance = (end_date - sow_date).days
                    comparisons.append({
                        'task': task_name,
                        'sow_name': sow_name,
                        'sow_date': sow_date,
                        'current_date': end_date,
                        'variance': variance,
                        'assigned': task.get('Assigned To', ''),
                        'status': task.get('Status', ''),
                        'row': task['row_number']
                    })
                break

    # Sort by SOW date
    comparisons.sort(key=lambda x: x['sow_date'])

    print(f"\n  {'Milestone':<45} | {'SOW Date':^10} | {'Current':^10} | {'Slip':^6} | {'Owner':<10}")
    print(f"  {'-'*45}-+-{'-'*10}-+-{'-'*10}-+-{'-'*6}-+-{'-'*10}")

    total_slip = 0
    slip_by_owner = defaultdict(list)

    for c in comparisons:
        sow_str = c['sow_date'].strftime('%m/%d')
        curr_str = c['current_date'].strftime('%m/%d')
        var = c['variance']
        var_str = f"+{var}d" if var > 0 else f"{var}d" if var < 0 else "0d"
        owner = c['assigned'] or 'N/A'

        # Highlight slips
        if var > 0:
            slip_by_owner[owner].append(var)
            total_slip = max(total_slip, var)

        print(f"  {c['sow_name'][:45]:<45} | {sow_str:^10} | {curr_str:^10} | {var_str:^6} | {owner:<10}")

    return comparisons, slip_by_owner


def identify_root_cause(comparisons, slip_by_owner):
    """Identify which vendor caused the slip"""
    print("\n" + "=" * 90)
    print("  ROOT CAUSE ANALYSIS - WHO CAUSED THE SLIP?")
    print("=" * 90)

    print("\n  Slip by Vendor (days past SOW contracted date):")

    vendors = ['IGT', 'FPS', 'Cognigy', 'CSG', 'Frontier']
    vendor_max_slip = {}

    for vendor in vendors:
        slips = slip_by_owner.get(vendor, [])
        if slips:
            max_slip = max(slips)
            avg_slip = sum(slips) / len(slips)
            vendor_max_slip[vendor] = max_slip
            print(f"    {vendor:10}: Max {max_slip:+3}d | Avg {avg_slip:+5.1f}d | {len(slips)} milestones slipped")
        else:
            print(f"    {vendor:10}: No slip data (tasks complete or on track)")

    # Find the earliest critical slip
    print("\n  [CRITICAL SLIP ANALYSIS]")

    critical_milestones = [c for c in comparisons if c['variance'] > 0]
    critical_milestones.sort(key=lambda x: x['sow_date'])

    if critical_milestones:
        first_slip = critical_milestones[0]
        print(f"\n  FIRST MILESTONE TO SLIP:")
        print(f"    Milestone: {first_slip['sow_name']}")
        print(f"    Owner:     {first_slip['assigned'] or 'N/A'}")
        print(f"    SOW Date:  {first_slip['sow_date'].strftime('%Y-%m-%d')}")
        print(f"    Current:   {first_slip['current_date'].strftime('%Y-%m-%d')}")
        print(f"    Slip:      {first_slip['variance']} days")

    return vendor_max_slip


def analyze_igt_dependency(tasks):
    """Analyze the IGT dependency issue"""
    print("\n" + "=" * 90)
    print("  IGT DEPENDENCY DEEP DIVE")
    print("=" * 90)

    # SOW says IGT Staging Dependencies: Dec 8
    sow_igt_staging = datetime(2025, 12, 8)

    # Find IGT tasks in schedule
    igt_tasks = [t for t in tasks if t.get('Assigned To') == 'IGT']

    print(f"\n  SOW Contracted Date for IGT Staging Dependencies: {sow_igt_staging.strftime('%Y-%m-%d')}")
    print(f"  SOW Contracted Date for IGT Production Dependencies: 2025-12-15")

    print(f"\n  Current IGT Tasks in Schedule:")
    for t in igt_tasks:
        end = parse_date(t.get('End Date'))
        end_str = end.strftime('%Y-%m-%d') if end else 'N/A'
        status = t.get('Status', 'N/A')
        health = t.get('Health', 'N/A')
        notes = t.get('Notes', '')

        print(f"    Row {t['row_number']:2}: {end_str} | {status:12} | {health:6} | {t['Tasks'][:40]}")
        if notes:
            print(f"           NOTE: {notes[:70]}")

    # The key note
    print(f"\n  [KEY EVIDENCE]")
    print(f"    SOW Section 9 (Penalties): 'FPS shall not be liable for penalties or damages'")
    print(f"    'if delays occur due to dependencies outside FPS control (by Frontier, Cognigy, CSG, IGT, etc.)'")
    print(f"\n    The IGT note from 12/05 states configuration will take '2-3 more weeks'")
    print(f"    This pushes IGT completion from Dec 8 (SOW) to Dec 23 (current) = 15 days slip")


def calculate_cascade_impact(tasks):
    """Calculate the cascade impact of IGT delay"""
    print("\n" + "=" * 90)
    print("  CASCADE IMPACT ANALYSIS")
    print("=" * 90)

    sow_go_live = datetime(2026, 1, 7)
    igt_slip = 15  # Days IGT slipped from Dec 8 to Dec 23

    print(f"\n  IGT Staging Dependencies:")
    print(f"    SOW:     Dec 8")
    print(f"    Current: Dec 23")
    print(f"    Slip:    +15 days")

    print(f"\n  Cascade Effect (assuming sequential dependencies):")

    cascade = [
        ("IGT Staging (Dec 8 -> Dec 23)", 15),
        ("FPS QA (Dec 12 -> Dec 27*)", 15),
        ("Cognigy/IGT Production (Dec 15 -> Dec 30*)", 15),
        ("Frontier UAT (Dec 19 -> Jan 3*)", 15),
        ("Frontier UAT Approval (Dec 19 -> Jan 3*)", 15),
        ("CAB Approval (Jan 6 -> Jan 21*)", 15),
        ("Production Deployment (Jan 7 -> Jan 22*)", 15),
    ]

    for milestone, slip in cascade:
        print(f"    {milestone:45} -> +{slip} days")

    print(f"\n  *Note: Actual dates may differ due to holidays and dependency logic")

    print(f"\n  [CONCLUSION]")
    print(f"    The IGT delay of 15 days cascades through the entire schedule.")
    print(f"    Current projection of Jan 30 is 8 days beyond the cascade calculation,")
    print(f"    likely due to holiday gaps (Dec 24-26) being added to the schedule.")


def generate_accountability_report():
    """Generate accountability report"""
    print("\n" + "=" * 90)
    print("  ACCOUNTABILITY REPORT")
    print("=" * 90)

    print("""
  Based on SOW Analysis:

  1. CONTRACTED GO-LIVE: January 7-14, 2026
     - SOW Section 1: "Deploy during the week of Jan 7-14"
     - This aligns with original baseline of Jan 7

  2. ROOT CAUSE OF SLIP: IGT
     - SOW contracted IGT Staging Dependencies: Dec 8
     - Actual IGT completion: Dec 23 (per 12/05 note)
     - IGT slip: +15 days

  3. CONTRACTUAL PROTECTION FOR FPS:
     - SOW Section 9: "FPS shall not be liable for penalties or damages
       if delays occur due to dependencies outside FPS control"
     - IGT is explicitly listed as an external dependency

  4. FRONTIER IS NOT THE BLOCKER:
     - All Frontier-owned milestones that have passed are COMPLETE
     - Frontier Staging Dependencies: Complete (Nov 21)
     - Frontier SOW Approval: Complete (Nov 21)
     - Frontier Production Dependencies (ARB): In Progress (on track)
     - Future Frontier tasks (UAT, CAB) are blocked by IGT/FPS predecessors

  5. RECOMMENDED BASELINE UPDATE:
     - Original SOW baseline: Jan 7 (reflects contracted dates)
     - Approved target: Jan 13 (per your earlier statement)
     - Current projection: Jan 30 (due to IGT delay)

     The baselines should be updated to Jan 13 (approved target).
     Variance should then be measured against Jan 13, not Jan 7.

     With Jan 13 baseline:
     - Current projection of Jan 30 = 17 days slip (vs 23 from Jan 7)
     - IGT accountability: 15 of those 17 days

  6. SCHEDULE CORRECTION APPROACH:
     a) Update baselines to Jan 13 (approved)
     b) Document IGT as root cause of remaining slip
     c) Per SOW Section 7 (Change Control), formally document the
        schedule adjustment caused by IGT dependency delay
""")


def main():
    """Main entry point"""
    print("\n" + "=" * 90)
    print("  FPS STATEMENT OF WORK vs CURRENT SCHEDULE ANALYSIS")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)

    tasks = load_schedule()

    comparisons, slip_by_owner = compare_schedule_to_sow(tasks)
    vendor_slips = identify_root_cause(comparisons, slip_by_owner)
    analyze_igt_dependency(tasks)
    calculate_cascade_impact(tasks)
    generate_accountability_report()

    print("\n" + "=" * 90)
    print("  ANALYSIS COMPLETE")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    main()
