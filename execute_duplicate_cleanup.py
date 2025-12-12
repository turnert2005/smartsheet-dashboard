"""
Execute Duplicate Cleanup - Delete duplicates and update occurrence counts
This script will:
1. Update occurrence counts on original/master rows
2. Add comments documenting recurrences
3. DELETE duplicate rows from the sheet
"""
import requests
from datetime import datetime
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052

# Column IDs
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_DATE_LOGGED = 7464884414140292
COL_NOTES = 2961284786769796
COL_OCCURRENCE_COUNT = 7996699210108804

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

# Duplicate mapping from analysis (duplicate_row_id -> original_row_id)
DUPLICATE_MAPPING = {
    # Format: duplicate_row_num: (duplicate_row_id, original_row_num, original_row_id)
    # These need to be populated from actual sheet data
}

def get_sheet_data():
    """Fetch sheet with all row data"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}'
    response = requests.get(url, headers=headers)
    return response.json()

def get_row_id_mapping(sheet):
    """Create mapping of row numbers to row IDs"""
    row_map = {}
    for row in sheet.get('rows', []):
        row_num = row.get('rowNumber')
        row_id = row.get('id')
        row_map[row_num] = row_id
    return row_map

def execute_cleanup():
    """Execute the full cleanup: update counts, add comments, delete duplicates"""
    print("=" * 70)
    print("EXECUTING DUPLICATE CLEANUP")
    print("=" * 70)
    print()

    print("Fetching current sheet data...")
    sheet = get_sheet_data()
    row_map = get_row_id_mapping(sheet)

    # Duplicate pairs identified from analysis
    # (duplicate_row_num, original_row_num)
    duplicate_pairs = [
        (21, 20),   # P3 Milestones
        (53, 48),   # IGT SIP Trunk Timeline
        (60, 44),   # Screen Pop Enhancement
        (62, 55),   # Azure Speech Keys
        (63, 56),   # Angela 800 Number
        (66, 58),   # Project Baseline Update
        (67, 54),   # Sprint Capacity
        (68, 57),   # QA UAT Execution
        (70, 56),   # Angela 800 Number (2nd duplicate)
        (75, 71),   # Create MS Loop Page
    ]

    # Build row ID lists
    duplicate_row_ids = []
    original_updates = {}  # original_row_id -> count_increment

    for dup_row, orig_row in duplicate_pairs:
        dup_id = row_map.get(dup_row)
        orig_id = row_map.get(orig_row)

        if dup_id and orig_id:
            duplicate_row_ids.append(dup_id)
            original_updates[orig_id] = original_updates.get(orig_id, 0) + 1
        else:
            print(f"  [WARNING] Could not find row IDs for pair ({dup_row}, {orig_row})")

    print(f"\nDuplicate rows to delete: {len(duplicate_row_ids)}")
    print(f"Original rows to update: {len(original_updates)}")

    # Step 1: Get current occurrence counts for originals
    print("\n--- Step 1: Reading current occurrence counts ---")
    rows_data = {}
    for row in sheet.get('rows', []):
        row_id = row.get('id')
        if row_id in original_updates:
            current_count = 1  # Default
            action_text = ""
            for cell in row.get('cells', []):
                if cell.get('columnId') == COL_OCCURRENCE_COUNT:
                    current_count = cell.get('value', 1) or 1
                if cell.get('columnId') == COL_ACTION_ITEM:
                    action_text = cell.get('value', '')[:50]
            rows_data[row_id] = {
                'current_count': current_count,
                'increment': original_updates[row_id],
                'action': action_text,
                'row_num': row.get('rowNumber')
            }
            print(f"  Row {row.get('rowNumber')}: Current count={current_count}, Adding {original_updates[row_id]}")

    # Step 2: Update occurrence counts on original rows
    print("\n--- Step 2: Updating occurrence counts ---")
    rows_to_update = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for row_id, data in rows_data.items():
        new_count = data['current_count'] + data['increment']
        comment = f"[{timestamp}] Occurrence count updated: {data['increment']} duplicate(s) merged"

        rows_to_update.append({
            'id': row_id,
            'cells': [
                {'columnId': COL_OCCURRENCE_COUNT, 'value': new_count},
                {'columnId': COL_NOTES, 'value': comment}
            ]
        })
        print(f"  Row {data['row_num']}: {data['current_count']} -> {new_count}")

    # Execute update
    if rows_to_update:
        update_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
        response = requests.put(update_url, headers=headers, json=rows_to_update)

        if response.status_code == 200:
            print(f"\n  [OK] Updated {len(rows_to_update)} original rows")
        else:
            print(f"\n  [ERROR] Failed to update: {response.status_code}")
            print(response.json())
            return

    # Step 3: Delete duplicate rows
    print("\n--- Step 3: Deleting duplicate rows ---")

    if duplicate_row_ids:
        ids_param = ','.join(map(str, duplicate_row_ids))
        delete_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows?ids={ids_param}'

        print(f"  Deleting {len(duplicate_row_ids)} rows...")
        response = requests.delete(delete_url, headers=headers)

        if response.status_code == 200:
            print(f"\n  [OK] Deleted {len(duplicate_row_ids)} duplicate rows")
        else:
            print(f"\n  [ERROR] Failed to delete: {response.status_code}")
            print(response.json())
            return

    # Summary
    print("\n" + "=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"  - Updated occurrence counts on {len(rows_to_update)} original rows")
    print(f"  - Deleted {len(duplicate_row_ids)} duplicate rows")
    print("\nOriginal rows now reflect total occurrences across all meetings.")

if __name__ == "__main__":
    # Safety confirmation
    print("This script will DELETE duplicate rows from the FPS Action Item Log.")
    print("Occurrence counts will be updated on original/master rows.")
    print()
    confirm = input("Type 'EXECUTE' to proceed: ")

    if confirm == 'EXECUTE':
        execute_cleanup()
    else:
        print("Aborted - no changes made")
