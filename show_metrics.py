"""
Real-Time Metrics Output Script
Displays current project metrics from the Task Sheet summary fields
"""

import smartsheet
from datetime import datetime
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


def get_metrics():
    """Fetch and display all metrics from the task sheet"""

    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    sheet = client.Sheets.get_sheet(TASK_SHEET_ID, include='summary')

    # Build a dict of summary fields
    metrics = {}
    for field in sheet.summary.fields:
        value = field.display_value if field.display_value else field.object_value
        metrics[field.title] = {
            'value': value,
            'id': field.id,
            'formula': field.formula
        }

    # Print formatted output
    print()
    print("=" * 70)
    print(f"  PHASE 2 - AGENTIC VOICE PROJECT METRICS")
    print(f"  As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # KPI Section
    print("\n--- KEY PERFORMANCE INDICATORS ---\n")

    project_health = metrics.get('Project Health', {}).get('value', 'N/A')
    variance = metrics.get('Project Variance', {}).get('value', 'N/A')
    target = metrics.get('Target Go-Live', {}).get('value', 'N/A')
    original = metrics.get('Original Go-Live', {}).get('value', 'N/A')

    # Parse date objects
    if isinstance(target, dict):
        target = target.get('value', 'N/A')
    if isinstance(original, dict):
        original = original.get('value', 'N/A')

    print(f"  Project Health:    {project_health}")
    print(f"  Project Variance:  {variance} days")
    print(f"  Target Go-Live:    {target}")
    print(f"  Original Go-Live:  {original}")

    # Health Counts
    print("\n--- HEALTH DISTRIBUTION ---\n")

    red = metrics.get('Total Red', {}).get('value', 0)
    yellow = metrics.get('Total Yellow', {}).get('value', 0)
    green = metrics.get('Total Green', {}).get('value', 0)
    total = metrics.get('Total Tasks', {}).get('value', 0)

    print(f"  Red:     {red} tasks")
    print(f"  Yellow:  {yellow} tasks")
    print(f"  Green:   {green} tasks")
    print(f"  Total:   {total} tasks")

    # Completion
    print("\n--- COMPLETION STATUS ---\n")

    pct_complete = metrics.get('% Complete', {}).get('value', 0)
    if isinstance(pct_complete, (int, float)):
        pct_complete = f"{float(pct_complete) * 100:.1f}%"

    overdue = metrics.get('Overdue Count', {}).get('value', 0)
    max_var = metrics.get('Max Variance', {}).get('value', 0)

    print(f"  % Complete:     {pct_complete}")
    print(f"  Overdue Tasks:  {overdue}")
    print(f"  Max Variance:   {max_var} days")

    # Vendor Progress
    print("\n--- VENDOR PROGRESS ---\n")

    vendors = ['FPS', 'IGT', 'Cognigy', 'CSG', 'Frontier']

    for vendor in vendors:
        field_name = f'{vendor} Complete'
        pct = metrics.get(field_name, {}).get('value', 0)

        # Handle string values like "0.42857"
        if isinstance(pct, str):
            try:
                pct = float(pct)
            except:
                pct = 0

        if isinstance(pct, (int, float)):
            pct_val = float(pct) * 100
            filled = int(pct_val / 10)
            empty = 10 - filled
            bar = "#" * filled + "-" * empty
            print(f"  {vendor:10} [{bar}] {pct_val:5.1f}%")
        else:
            print(f"  {vendor:10} N/A")

    # Summary Field IDs for Dashboard Reference
    print("\n--- SUMMARY FIELD IDs (for Dashboard Widgets) ---\n")

    important_fields = [
        'Project Health', 'Project Variance', 'Target Go-Live', 'Original Go-Live',
        '% Complete', 'Total Red', 'Total Yellow', 'Total Green',
        'FPS Complete', 'IGT Complete', 'Cognigy Complete', 'CSG Complete', 'Frontier Complete'
    ]

    for field_name in important_fields:
        field = metrics.get(field_name, {})
        if field:
            print(f"  {field_name:20} ID: {field.get('id')}")

    print("\n" + "=" * 70)
    print(f"  Sheet ID: {TASK_SHEET_ID}")
    print(f"  Sheet Name: {sheet.name}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    get_metrics()
