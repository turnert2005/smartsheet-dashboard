"""
Fix Summary Row End Date Formulas
Updates all parent/summary rows to use =MAX(CHILDREN()) for End Date column.

ISSUE: Currently all 23 summary rows have:
  - Start Date: =MIN(CHILDREN())  ✓ Correct
  - End Date: MANUAL VALUE        ✗ Will drift if child dates change

FIX: Update End Date to =MAX(CHILDREN()) for automatic rollup.

AFFECTED ROWS (23 total):
  Phase Level: 1, 41, 50
  Section Level: 2, 5, 8, 10, 13, 17, 22, 25, 32, 38, 42, 45, 48, 51, 54, 57, 61, 66, 69, 72

RUN ON TEST COPY FIRST.
"""
import requests
import json
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID

# Set to True to execute, False for dry-run
EXECUTE = False

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

# Get sheet
url = f'https://api.smartsheet.com/2.0/sheets/{TASK_SHEET_ID}'
response = requests.get(url, headers=headers)
sheet = response.json()

# Find column IDs
col_by_name = {col['title']: col['id'] for col in sheet.get('columns', [])}
end_date_col_id = col_by_name.get('End Date')
task_col_id = col_by_name.get('Tasks')

print(f'End Date Column ID: {end_date_col_id}')
print()

# Identify parent rows (rows that have children)
row_ids_with_children = set()
for row in sheet.get('rows', []):
    parent_id = row.get('parentId')
    if parent_id:
        row_ids_with_children.add(parent_id)

# Build list of summary rows to update
summary_rows = []
for row in sheet.get('rows', []):
    row_id = row.get('id')
    row_num = row.get('rowNumber')

    if row_id in row_ids_with_children:
        # This is a parent row
        task_name = ''
        current_end = ''
        current_formula = ''

        for cell in row.get('cells', []):
            if cell.get('columnId') == task_col_id:
                task_name = (cell.get('value') or '')[:45]
            if cell.get('columnId') == end_date_col_id:
                current_end = cell.get('value') or ''
                current_formula = cell.get('formula') or ''

        # Check if already using CHILDREN formula
        has_formula = 'CHILDREN' in current_formula if current_formula else False

        summary_rows.append({
            'row_num': row_num,
            'row_id': row_id,
            'task': task_name,
            'current_end': str(current_end)[:10] if current_end else '',
            'current_formula': current_formula,
            'has_formula': has_formula
        })

# Sort by row number
summary_rows.sort(key=lambda x: x['row_num'])

print('='*100)
print('SUMMARY ROW END DATE FORMULA UPDATE PLAN')
print('='*100)
print()
print(f'{"Row":4} | {"Task":45} | {"Current End":12} | {"Has Formula":12} | {"Action":10}')
print('-'*100)

rows_to_update = []
for r in summary_rows:
    action = 'SKIP' if r['has_formula'] else 'UPDATE'
    print(f"{r['row_num']:4} | {r['task']:45} | {r['current_end']:12} | {'Yes' if r['has_formula'] else 'No':12} | {action:10}")

    if not r['has_formula']:
        rows_to_update.append({
            'id': r['row_id'],
            'cells': [
                {
                    'columnId': end_date_col_id,
                    'formula': '=MAX(CHILDREN())'
                }
            ]
        })

print()
print(f'Total summary rows: {len(summary_rows)}')
print(f'Rows already using formula: {len([r for r in summary_rows if r["has_formula"]])}')
print(f'Rows to update: {len(rows_to_update)}')
print()

if not EXECUTE:
    print('='*100)
    print('DRY RUN MODE - No changes made')
    print('Set EXECUTE = True to apply changes')
    print('='*100)
elif len(rows_to_update) == 0:
    print('='*100)
    print('NO UPDATES NEEDED - All summary rows already use formulas')
    print('='*100)
else:
    print('='*100)
    print('EXECUTING UPDATES...')
    print('='*100)

    # Execute update
    update_url = f'https://api.smartsheet.com/2.0/sheets/{TASK_SHEET_ID}/rows'
    response = requests.put(update_url, headers=headers, json=rows_to_update)

    if response.status_code == 200:
        result = response.json()
        print(f'SUCCESS: Updated {len(result.get("result", []))} rows')
        print()
        print('Formula applied: =MAX(CHILDREN())')
        print()
        print('Updated row IDs:')
        for row in result.get('result', []):
            print(f'  {row.get("id")}')
    else:
        print(f'ERROR: {response.status_code}')
        print(json.dumps(response.json(), indent=2))

print()
print(f'Sheet URL: https://app.smartsheet.com/sheets/{TASK_SHEET_ID}')
