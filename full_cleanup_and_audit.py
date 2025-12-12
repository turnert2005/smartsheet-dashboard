"""
Full Cleanup and Audit Setup for FPS Action Item Log
1. Add audit columns (Created By, Created Date, Modified By, Modified Date)
2. Clean up remaining semantic duplicates
3. Remove strikethroughs from non-duplicate rows
4. Analyze row creation sources
"""
import requests
import json
from datetime import datetime
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052

# Column IDs
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_NOTES = 2961284786769796
COL_OCCURRENCE_COUNT = 7996699210108804

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_sheet_data():
    """Fetch sheet with all row data including createdBy/modifiedBy"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}?include=format,rowPermalink,writerInfo'
    response = requests.get(url, headers=headers)
    return response.json()

def get_columns():
    """Get current columns"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/columns'
    response = requests.get(url, headers=headers)
    return response.json()

def add_system_columns():
    """Add system columns for audit trail"""
    print("=" * 70)
    print("ADDING AUDIT COLUMNS")
    print("=" * 70)

    # Get existing columns
    cols = get_columns()
    existing_types = {c.get('systemColumnType') for c in cols.get('data', [])}
    existing_titles = {c.get('title') for c in cols.get('data', [])}

    columns_to_add = []

    # Check for system columns
    system_columns = [
        ('CREATED_BY', 'Created By'),
        ('CREATED_DATE', 'Created Date'),
        ('MODIFIED_BY', 'Modified By'),
        ('MODIFIED_DATE', 'Modified Date'),
    ]

    for sys_type, title in system_columns:
        if sys_type not in existing_types and title not in existing_titles:
            columns_to_add.append({
                'title': title,
                'type': 'TEXT_NUMBER' if 'BY' in sys_type else 'DATE',
                'systemColumnType': sys_type
            })
            print(f"  Will add: {title} ({sys_type})")
        else:
            print(f"  Already exists: {title}")

    if columns_to_add:
        url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/columns'
        for col in columns_to_add:
            response = requests.post(url, headers=headers, json=col)
            if response.status_code == 200:
                print(f"  [OK] Added {col['title']}")
            else:
                print(f"  [ERROR] Failed to add {col['title']}: {response.status_code}")
                print(response.json())
    else:
        print("  All audit columns already exist")

    return True

def analyze_row_creators(sheet):
    """Analyze who created each row"""
    print("\n" + "=" * 70)
    print("ROW CREATION ANALYSIS")
    print("=" * 70)

    creators = {}
    rows_by_creator = {}

    for row in sheet.get('rows', []):
        row_num = row.get('rowNumber')
        created_by = row.get('createdBy', {})
        created_at = row.get('createdAt', '')
        modified_by = row.get('modifiedBy', {})

        creator_email = created_by.get('email', 'Unknown')
        creator_name = created_by.get('name', creator_email)

        if creator_email not in creators:
            creators[creator_email] = {
                'name': creator_name,
                'count': 0,
                'rows': []
            }

        creators[creator_email]['count'] += 1
        creators[creator_email]['rows'].append(row_num)

    print("\nRows created by each user:")
    print("-" * 70)

    for email, data in sorted(creators.items(), key=lambda x: -x[1]['count']):
        print(f"\n{data['name']} ({email})")
        print(f"  Total rows created: {data['count']}")
        print(f"  Row numbers: {', '.join(map(str, sorted(data['rows'])))}")

    return creators

def clean_semantic_duplicate():
    """Clean up Row 44 vs 48 semantic duplicate"""
    print("\n" + "=" * 70)
    print("CLEANING SEMANTIC DUPLICATE (Row 44 vs 48)")
    print("=" * 70)

    sheet = get_sheet_data()

    # Find row 44 and row 48
    row_44_id = None
    row_48_id = None
    row_48_count = 1

    for row in sheet.get('rows', []):
        row_num = row.get('rowNumber')
        if row_num == 44:
            row_44_id = row.get('id')
        elif row_num == 48:
            row_48_id = row.get('id')
            for cell in row.get('cells', []):
                if cell.get('columnId') == COL_OCCURRENCE_COUNT:
                    row_48_count = cell.get('value', 1) or 1

    if not row_44_id or not row_48_id:
        print("  Could not find both rows")
        return False

    # Update Row 48 occurrence count (add 1 for absorbed duplicate)
    new_count = int(row_48_count) + 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    update_payload = [{
        'id': row_48_id,
        'cells': [
            {'columnId': COL_OCCURRENCE_COUNT, 'value': new_count},
            {'columnId': COL_NOTES, 'value': f"[{timestamp}] Merged Row 44 (semantic duplicate)"}
        ]
    }]

    update_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
    response = requests.put(update_url, headers=headers, json=update_payload)

    if response.status_code == 200:
        print(f"  [OK] Updated Row 48 occurrence count: {row_48_count} -> {new_count}")
    else:
        print(f"  [ERROR] Failed to update Row 48: {response.status_code}")
        return False

    # Delete Row 44
    delete_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows?ids={row_44_id}'
    response = requests.delete(delete_url, headers=headers)

    if response.status_code == 200:
        print(f"  [OK] Deleted Row 44 (duplicate)")
    else:
        print(f"  [ERROR] Failed to delete Row 44: {response.status_code}")
        return False

    return True

def remove_strikethroughs():
    """Remove strikethroughs from non-duplicate rows"""
    print("\n" + "=" * 70)
    print("REMOVING STRIKETHROUGHS")
    print("=" * 70)

    sheet = get_sheet_data()

    # Find rows with strikethrough
    rows_to_fix = []

    for row in sheet.get('rows', []):
        row_id = row.get('id')
        row_num = row.get('rowNumber')

        for cell in row.get('cells', []):
            if cell.get('columnId') == COL_ACTION_ITEM:
                cell_format = cell.get('format', '')
                if cell_format:
                    parts = cell_format.split(',')
                    if len(parts) > 5 and parts[5] == '1':
                        # Has strikethrough - remove it
                        parts[5] = ''  # Clear strikethrough
                        new_format = ','.join(parts)
                        rows_to_fix.append({
                            'id': row_id,
                            'row_num': row_num,
                            'new_format': new_format
                        })

    if not rows_to_fix:
        print("  No strikethroughs found")
        return True

    print(f"  Found {len(rows_to_fix)} rows with strikethrough")

    # Update rows to remove strikethrough
    update_payload = []
    for row_info in rows_to_fix:
        update_payload.append({
            'id': row_info['id'],
            'cells': [{
                'columnId': COL_ACTION_ITEM,
                'format': row_info['new_format']
            }]
        })

    update_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
    response = requests.put(update_url, headers=headers, json=update_payload)

    if response.status_code == 200:
        print(f"  [OK] Removed strikethrough from {len(rows_to_fix)} rows:")
        for r in rows_to_fix:
            print(f"      Row {r['row_num']}")
    else:
        print(f"  [ERROR] Failed to remove strikethroughs: {response.status_code}")
        print(response.json())
        return False

    return True

def main():
    print("=" * 70)
    print("FULL CLEANUP AND AUDIT SETUP")
    print("=" * 70)
    print()

    # Step 1: Add audit columns
    add_system_columns()

    # Step 2: Get fresh data with creator info
    print("\nFetching sheet data with creator info...")
    sheet = get_sheet_data()

    # Step 3: Analyze row creators
    creators = analyze_row_creators(sheet)

    # Step 4: Clean semantic duplicate
    clean_semantic_duplicate()

    # Step 5: Remove strikethroughs
    remove_strikethroughs()

    # Summary
    print("\n" + "=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print("\nAudit columns added - you can now see:")
    print("  - Created By: Who created each row")
    print("  - Created Date: When each row was created")
    print("  - Modified By: Who last modified each row")
    print("  - Modified Date: When each row was last modified")
    print("\nThis will help identify if duplicates come from manual entry vs API scripts.")

if __name__ == "__main__":
    main()
