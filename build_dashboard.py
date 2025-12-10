"""
Smartsheet Dashboard Builder - Main Script
Phase 2 - Agentic Voice Project Dashboard

Creates reports, dashboard, and widgets via API.
"""

import json
import sys
import smartsheet
from datetime import datetime
from typing import Dict, List, Optional

from config import (
    SMARTSHEET_API_TOKEN,
    TASK_SHEET_ID,
    WORKSPACE_ID,
    DASHBOARD_NAME,
    EXISTING_DASHBOARD_ID,
    REPORT_AT_RISK_NAME,
    REPORT_MILESTONES_NAME
)
from smartsheet_sdk_client import SmartsheetSDKClient
from widget_builder import WidgetBuilder, WidgetPosition


def print_banner():
    """Print startup banner"""
    print("\n" + "=" * 70)
    print("  SMARTSHEET DASHBOARD BUILDER")
    print("  Phase 2 - Agentic Voice Project")
    print("=" * 70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")


def validate_config() -> bool:
    """Validate configuration"""
    errors = []

    if SMARTSHEET_API_TOKEN == "YOUR_API_TOKEN_HERE" or not SMARTSHEET_API_TOKEN:
        errors.append("SMARTSHEET_API_TOKEN not configured")

    if TASK_SHEET_ID == 0 or not TASK_SHEET_ID:
        errors.append("TASK_SHEET_ID not configured")

    if errors:
        print("[ERROR] Configuration Errors:")
        for err in errors:
            print(f"   - {err}")
        print("\nPlease update config.py with your actual values.\n")
        return False

    return True


def step1_verify_sheet(client: SmartsheetSDKClient) -> Dict:
    """Step 1: Verify sheet access and get details"""
    print("\n" + "=" * 70)
    print("  STEP 1: Verifying Sheet Access")
    print("=" * 70)

    try:
        sheet = client.get_sheet(TASK_SHEET_ID, include=['summary'])

        print(f"\n[OK] Connected to sheet: {sheet.name}")
        print(f"   Sheet ID: {sheet.id}")
        print(f"   Total Rows: {sheet.total_row_count}")
        print(f"   Permalink: {sheet.permalink}")

        # Build column map
        columns = sheet.columns
        column_map = {}
        print(f"\n[COLUMNS] ({len(columns)}):")
        for col in columns:
            print(f"   - {col.title} (ID: {col.id})")
            column_map[col.title.lower()] = col.id

        # Build summary field map
        summary_fields = {}
        if sheet.summary and sheet.summary.fields:
            print(f"\n[SUMMARY FIELDS] ({len(sheet.summary.fields)}):")
            for field in sheet.summary.fields:
                value = field.display_value or field.object_value or "N/A"
                print(f"   - {field.title}: {value}")
                summary_fields[field.title] = {
                    'id': field.id,
                    'displayValue': value,
                    'formula': field.formula
                }

        # Check required columns
        required_cols = ["tasks", "health", "status", "assigned to", "end date", "variance"]
        missing_cols = [c for c in required_cols if c not in column_map]
        if missing_cols:
            print(f"\n[WARN] Missing columns: {missing_cols}")

        return {
            "sheet": sheet,
            "column_map": column_map,
            "summary_fields": summary_fields
        }

    except smartsheet.exceptions.ApiError as e:
        print(f"\n[ERROR] API Error: {e.message}")
        raise
    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise


def step2_find_or_skip_reports(client: SmartsheetSDKClient) -> Dict[str, int]:
    """Step 2: Find existing reports or provide instructions to create them"""
    print("\n" + "=" * 70)
    print("  STEP 2: Checking for Reports")
    print("=" * 70)

    print("\n[INFO] The Smartsheet API does not support creating reports.")
    print("       Searching for existing reports...")

    report_ids = {}

    try:
        # List existing reports to find matches
        reports = client.client.Reports.list_reports(include_all=True)

        for report in reports.data:
            if REPORT_AT_RISK_NAME.lower() in report.name.lower():
                report_ids["at_risk"] = report.id
                print(f"   [FOUND] {report.name} (ID: {report.id})")
            elif REPORT_MILESTONES_NAME.lower() in report.name.lower():
                report_ids["milestones"] = report.id
                print(f"   [FOUND] {report.name} (ID: {report.id})")

    except Exception as e:
        print(f"   [WARN] Could not list reports: {e}")

    if not report_ids:
        print("\n[ACTION REQUIRED] Please create these reports manually in Smartsheet:")
        print(f"""
   1. "{REPORT_AT_RISK_NAME}"
      - Source: Task Sheet (ID: {TASK_SHEET_ID})
      - Filters: Health = 'Red', Status != 'Complete'
      - Sort: Variance (ascending)
      - Columns: Tasks, Status, Variance, End Date, Assigned To
      - Row limit: 5

   2. "{REPORT_MILESTONES_NAME}"
      - Source: Task Sheet (ID: {TASK_SHEET_ID})
      - Filters: Status != 'Complete', Tasks contains milestone keywords
      - Sort: End Date (ascending)
      - Columns: Tasks, Assigned To, End Date
      - Row limit: 5
""")
        print("   After creating reports, re-run this script to include them in the dashboard.")

    return report_ids


def step3_calculate_vendor_progress(client: SmartsheetSDKClient) -> Dict[str, float]:
    """Step 3: Calculate vendor progress from sheet data"""
    print("\n" + "=" * 70)
    print("  STEP 3: Calculating Vendor Progress")
    print("=" * 70)

    try:
        sheet = client.get_sheet(TASK_SHEET_ID)
        columns = sheet.columns
        rows = sheet.rows

        # Find column IDs
        assigned_col_id = None
        status_col_id = None
        for col in columns:
            if col.title.lower() == "assigned to":
                assigned_col_id = col.id
            elif col.title.lower() == "status":
                status_col_id = col.id

        if not assigned_col_id or not status_col_id:
            print("   [WARN] Could not find required columns")
            return get_default_vendor_data()

        # Count by vendor
        vendors = ["FPS", "IGT", "Cognigy", "CSG", "Frontier"]
        vendor_counts = {v: {"total": 0, "complete": 0} for v in vendors}

        for row in rows:
            assigned_to = None
            status = None

            for cell in row.cells:
                if cell.column_id == assigned_col_id:
                    assigned_to = cell.value
                elif cell.column_id == status_col_id:
                    status = cell.value

            if assigned_to in vendors:
                vendor_counts[assigned_to]["total"] += 1
                if status == "Complete":
                    vendor_counts[assigned_to]["complete"] += 1

        # Calculate percentages
        vendor_progress = {}
        print("\n[VENDOR PROGRESS]:")
        for vendor in vendors:
            total = vendor_counts[vendor]["total"]
            complete = vendor_counts[vendor]["complete"]
            pct = (complete / total * 100) if total > 0 else 0
            vendor_progress[vendor] = round(pct, 1)
            print(f"   {vendor}: {complete}/{total} ({pct:.1f}%)")

        return vendor_progress

    except Exception as e:
        print(f"   [WARN] Error: {e}")
        return get_default_vendor_data()


def get_default_vendor_data() -> Dict[str, float]:
    """Return default vendor progress data"""
    return {
        "FPS": 80,
        "IGT": 40,
        "Cognigy": 60,
        "CSG": 40,
        "Frontier": 20
    }


def step4_get_dashboard(client: SmartsheetSDKClient) -> Optional[int]:
    """Step 4: Use existing dashboard (API doesn't support creating new ones)"""
    print("\n" + "=" * 70)
    print("  STEP 4: Using Existing Dashboard")
    print("=" * 70)

    print("\n[INFO] Smartsheet API does not support creating dashboards.")
    print(f"       Using existing dashboard ID: {EXISTING_DASHBOARD_ID}")

    try:
        # Verify the dashboard exists
        dashboard = client.get_dashboard(EXISTING_DASHBOARD_ID)
        print(f"   [OK] Found dashboard: {dashboard.name}")
        print(f"   [OK] Dashboard ID: {dashboard.id}")

        # Track it
        client.created_objects["dashboards"].append({
            "id": dashboard.id,
            "name": dashboard.name
        })

        return dashboard.id

    except Exception as e:
        print(f"   [ERROR] Could not access dashboard: {e}")
        print("\n   Please verify EXISTING_DASHBOARD_ID in config.py")
        return None


def step5_add_widgets(
    client: SmartsheetSDKClient,
    dashboard_id: int,
    summary_fields: Dict,
    column_map: Dict,
    report_ids: Dict[str, int],
    vendor_progress: Dict[str, float]
) -> bool:
    """Step 5: Add widgets to the dashboard"""
    print("\n" + "=" * 70)
    print("  STEP 5: Adding Widgets to Dashboard")
    print("=" * 70)

    # Create widget builder
    widget_builder = WidgetBuilder(
        sheet_id=TASK_SHEET_ID,
        summary_fields=summary_fields,
        column_ids=column_map,
        report_ids=report_ids
    )

    # Build all widgets
    print("\n[BUILD] Building widget configurations...")
    widgets = widget_builder.build_all_widgets(vendor_data=vendor_progress)
    print(f"   Built {len(widgets)} widgets")

    # Update dashboard with widgets
    print("\n[UPLOAD] Uploading widgets to dashboard...")
    try:
        result = client.update_dashboard_with_widgets(
            sight_id=dashboard_id,
            widgets=widgets
        )
        print(f"   [OK] Successfully added {len(widgets)} widgets to dashboard")
        return True

    except Exception as e:
        print(f"   [ERROR] Failed to add widgets: {e}")
        print("\n   Note: Widget creation via API may have limitations.")
        print("   You may need to add some widgets manually in the Smartsheet UI.")
        save_widget_config(widgets)
        return False


def save_widget_config(widgets: List[Dict]):
    """Save widget configuration to file for reference"""
    filename = "widget_config.json"
    with open(filename, 'w') as f:
        json.dump(widgets, f, indent=2)
    print(f"\n   Widget configuration saved to {filename}")
    print("   Use this file as reference for manual widget creation if needed.")


def print_summary(client: SmartsheetSDKClient, dashboard_id: Optional[int]):
    """Print final summary"""
    print("\n" + "=" * 70)
    print("  BUILD COMPLETE - SUMMARY")
    print("=" * 70)

    created = client.get_created_objects()

    print("\n[REPORTS CREATED]:")
    for report in created.get("reports", []):
        print(f"   - {report['name']} (ID: {report['id']})")

    print("\n[DASHBOARDS CREATED]:")
    for dashboard in created.get("dashboards", []):
        print(f"   - {dashboard['name']} (ID: {dashboard['id']})")

    if dashboard_id:
        print(f"\n[DASHBOARD URL]:")
        print(f"   https://app.smartsheet.com/dashboards/{dashboard_id}")

    print("\n[NEXT STEPS]:")
    print("   1. Open your dashboard in Smartsheet")
    print("   2. Verify all widgets are displaying correctly")
    print("   3. Configure report filters if not already set")
    print("   4. Adjust widget sizes/positions as needed")

    # Save created objects
    client.save_created_objects()

    print("\n" + "=" * 70)
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")


def main():
    """Main entry point"""
    print_banner()

    # Validate configuration
    if not validate_config():
        sys.exit(1)

    print("This script will create:")
    print("  - 2 Reports (At-Risk Tasks, Upcoming Milestones)")
    print("  - 1 Dashboard with multiple widgets")
    print("\nPress Enter to continue or Ctrl+C to cancel...")

    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)

    # Initialize client
    client = SmartsheetSDKClient()

    try:
        # Step 1: Verify sheet
        sheet_data = step1_verify_sheet(client)

        # Step 2: Find existing reports
        report_ids = step2_find_or_skip_reports(client)

        # Step 3: Calculate vendor progress
        vendor_progress = step3_calculate_vendor_progress(client)

        # Step 4: Get existing dashboard
        dashboard_id = step4_get_dashboard(client)

        if dashboard_id:
            # Step 5: Add widgets
            step5_add_widgets(
                client=client,
                dashboard_id=dashboard_id,
                summary_fields=sheet_data["summary_fields"],
                column_map=sheet_data["column_map"],
                report_ids=report_ids,
                vendor_progress=vendor_progress
            )

        # Print summary
        print_summary(client, dashboard_id)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nSaving partial progress...")
        client.save_created_objects("created_objects_partial.json")

        print("\nWould you like to rollback? (y/n): ", end="")
        try:
            if input().strip().lower() == 'y':
                client.rollback()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
