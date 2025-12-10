"""
Report Data Generator
Generates the data for reports since the API doesn't support creating reports.
Shows Top 5 At-Risk Tasks and Upcoming Milestones from sheet data.
"""

import smartsheet
from datetime import datetime
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


def get_report_data():
    """Fetch sheet data and generate report content"""

    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    sheet = client.Sheets.get_sheet(TASK_SHEET_ID)

    # Build column ID map
    columns = {}
    col_id_to_name = {}
    for col in sheet.columns:
        columns[col.title.lower()] = col.id
        col_id_to_name[col.id] = col.title

    # Extract row data
    tasks_data = []
    for row in sheet.rows:
        row_data = {}
        for cell in row.cells:
            col_name = col_id_to_name.get(cell.column_id, '')
            row_data[col_name.lower()] = cell.value
        tasks_data.append(row_data)

    print()
    print("=" * 80)
    print(f"  REPORT DATA GENERATOR - Phase 2 Agentic Voice")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # =============================================
    # REPORT 1: Top 5 At-Risk Tasks
    # =============================================
    print("\n" + "-" * 80)
    print("  REPORT: TOP 5 AT-RISK TASKS")
    print("  Filters: Health = 'Red', Status != 'Complete'")
    print("  Sort: Variance (ascending - most negative first)")
    print("-" * 80 + "\n")

    # Filter: Health = Red AND Status != Complete
    at_risk = [
        t for t in tasks_data
        if t.get('health') == 'Red' and t.get('status') != 'Complete' and t.get('tasks')
    ]

    # Sort by variance (ascending = most negative first)
    at_risk_sorted = sorted(
        at_risk,
        key=lambda x: x.get('variance') if x.get('variance') is not None else 0
    )[:5]

    print(f"{'Task':<40} {'Status':<15} {'Variance':<10} {'End Date':<12} {'Assigned To'}")
    print("-" * 95)

    for task in at_risk_sorted:
        name = str(task.get('tasks', ''))[:38]
        status = str(task.get('status', ''))[:13]
        variance = task.get('variance', '')
        end_date = task.get('end date', '')
        if hasattr(end_date, 'strftime'):
            end_date = end_date.strftime('%Y-%m-%d')
        elif isinstance(end_date, str) and len(end_date) > 10:
            end_date = end_date[:10]
        assigned = str(task.get('assigned to', ''))[:15]

        print(f"{name:<40} {status:<15} {str(variance):<10} {str(end_date):<12} {assigned}")

    print(f"\nTotal at-risk tasks (Red, not Complete): {len(at_risk)}")

    # =============================================
    # REPORT 2: Upcoming Milestones
    # =============================================
    print("\n" + "-" * 80)
    print("  REPORT: UPCOMING MILESTONES")
    print("  Filters: Status != 'Complete', Task contains milestone keywords")
    print("  Sort: End Date (ascending)")
    print("-" * 80 + "\n")

    # Filter: Status != Complete AND task name contains milestone keywords
    milestone_keywords = ['complete', 'approval', 'deployment', 'go-live', 'launch', 'release', 'milestone', 'sign-off', 'handoff']

    milestones = []
    for t in tasks_data:
        task_name = str(t.get('tasks', '')).lower()
        status = t.get('status', '')

        if status != 'Complete' and t.get('tasks'):
            # Check if task contains any milestone keyword
            if any(kw in task_name for kw in milestone_keywords):
                milestones.append(t)

    # Sort by end date ascending
    def get_date_key(x):
        ed = x.get('end date')
        if ed is None:
            return datetime(2099, 12, 31)
        if hasattr(ed, 'date'):
            return ed
        return datetime(2099, 12, 31)

    milestones_sorted = sorted(milestones, key=get_date_key)[:5]

    print(f"{'Task':<50} {'Assigned To':<15} {'End Date'}")
    print("-" * 80)

    for task in milestones_sorted:
        name = str(task.get('tasks', ''))[:48]
        assigned = str(task.get('assigned to', ''))[:13]
        end_date = task.get('end date', '')
        if hasattr(end_date, 'strftime'):
            end_date = end_date.strftime('%Y-%m-%d')
        elif isinstance(end_date, str) and len(end_date) > 10:
            end_date = end_date[:10]

        print(f"{name:<50} {assigned:<15} {str(end_date)}")

    print(f"\nTotal milestone tasks found: {len(milestones)}")

    # =============================================
    # MANUAL REPORT CREATION INSTRUCTIONS
    # =============================================
    print("\n" + "=" * 80)
    print("  MANUAL REPORT CREATION INSTRUCTIONS")
    print("=" * 80)

    print("""
The Smartsheet API does NOT support creating reports programmatically.
Please create these reports manually in the Smartsheet UI:

REPORT 1: "Top 5 At-Risk Tasks"
-------------------------------
1. Click Create (+) > Report
2. Name: "Top 5 At-Risk Tasks"
3. Add Source Sheet: "1. Phase 2 - Agentic Voice Task Sheet"
4. Add Filters:
   - Health equals "Red"
   - Status does not equal "Complete"
5. Set Sort: Variance (Ascending)
6. Select Columns: Tasks, Status, Variance, End Date, Assigned To
7. Optional: Set row limit to 5 (in Display Options)
8. Save

REPORT 2: "Upcoming Milestones"
-------------------------------
1. Click Create (+) > Report
2. Name: "Upcoming Milestones"
3. Add Source Sheet: "1. Phase 2 - Agentic Voice Task Sheet"
4. Add Filters:
   - Status does not equal "Complete"
   - Tasks contains "Complete" OR "Approval" OR "Deployment"
     (Use multiple OR conditions or a custom formula)
5. Set Sort: End Date (Ascending)
6. Select Columns: Tasks, Assigned To, End Date
7. Optional: Set row limit to 5
8. Save

After creating the reports, you can add them as Report Widgets to your dashboard.
""")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    get_report_data()
