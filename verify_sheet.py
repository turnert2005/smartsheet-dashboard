"""
Sheet Verification Script
Verifies access to the task sheet and displays current configuration
"""

import json
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID
from smartsheet_client import SmartsheetClient


def verify_sheet():
    """Verify sheet access and display details"""

    if SMARTSHEET_API_TOKEN == "YOUR_API_TOKEN_HERE":
        print("❌ Please configure your API token in config.py")
        return

    if TASK_SHEET_ID == 0:
        print("❌ Please configure your sheet ID in config.py")
        return

    print("Connecting to Smartsheet API...")
    client = SmartsheetClient()

    try:
        # Get sheet with summary
        print(f"\nFetching sheet {TASK_SHEET_ID}...")
        sheet = client.get_sheet(TASK_SHEET_ID, include=["summary"])

        print("\n" + "=" * 60)
        print("SHEET DETAILS")
        print("=" * 60)
        print(f"Name: {sheet.get('name')}")
        print(f"ID: {sheet.get('id')}")
        print(f"Total Rows: {sheet.get('totalRowCount', 0)}")
        print(f"Access Level: {sheet.get('accessLevel')}")
        print(f"Permalink: {sheet.get('permalink')}")

        # Columns
        columns = sheet.get("columns", [])
        print(f"\n📋 COLUMNS ({len(columns)}):")
        print("-" * 40)
        for col in columns:
            col_type = col.get("type", "UNKNOWN")
            options = col.get("options", [])
            print(f"  {col.get('title')}")
            print(f"    ID: {col.get('id')}")
            print(f"    Type: {col_type}")
            if options:
                print(f"    Options: {options}")
            print()

        # Summary Fields
        summary = sheet.get("summary", {})
        summary_fields = summary.get("fields", [])
        print(f"\n📊 SUMMARY FIELDS ({len(summary_fields)}):")
        print("-" * 40)
        for field in summary_fields:
            title = field.get("title", "Untitled")
            field_type = field.get("type", "UNKNOWN")
            display_value = field.get("displayValue", field.get("objectValue", "N/A"))
            formula = field.get("formula", "")

            print(f"  {title}")
            print(f"    ID: {field.get('id')}")
            print(f"    Type: {field_type}")
            print(f"    Value: {display_value}")
            if formula:
                print(f"    Formula: {formula}")
            print()

        # Save to JSON for reference
        output = {
            "sheet_id": sheet.get("id"),
            "sheet_name": sheet.get("name"),
            "columns": [
                {
                    "id": col.get("id"),
                    "title": col.get("title"),
                    "type": col.get("type")
                }
                for col in columns
            ],
            "summary_fields": [
                {
                    "id": field.get("id"),
                    "title": field.get("title"),
                    "type": field.get("type"),
                    "displayValue": field.get("displayValue"),
                    "formula": field.get("formula")
                }
                for field in summary_fields
            ]
        }

        with open("sheet_details.json", "w") as f:
            json.dump(output, f, indent=2)
        print("\n✅ Sheet details saved to sheet_details.json")

        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETE")
        print("=" * 60)
        print("✅ Sheet access verified")
        print(f"✅ Found {len(columns)} columns")
        print(f"✅ Found {len(summary_fields)} summary fields")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    verify_sheet()
