"""
Fix IGT Staging Predecessors (Rows 26-31)
Updates predecessor relationships per approved recommendations.

CHANGES:
  Row 26 (1.8.1 Configure 800 number):     NONE → 25SS (parallel with parent)
  Row 27 (1.8.2 Set up SIP trunks):        NONE → 25SS (parallel with parent - CRITICAL)
  Row 28 (1.8.3 Configure Signal API):     NONE → 27SS (parallel to SIP setup)
  Row 29 (1.8.4 Complete queue mapping):   NONE → 27SS (parallel to SIP setup)
  Row 30 (1.8.5 Provision 8 DID numbers):  NONE → 27FS (after SIP trunks)
  Row 31 (1.8.6 Validate Screen Pop):      28FS → 28FS,30FS (requires both)

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

# Get sheet to find row IDs
url = f'https://api.smartsheet.com/2.0/sheets/{TASK_SHEET_ID}'
response = requests.get(url, headers=headers)
sheet = response.json()

# Find column IDs
col_by_name = {col['title']: col['id'] for col in sheet.get('columns', [])}
pred_col_id = col_by_name.get('Predecessors')

print(f'Predecessors Column ID: {pred_col_id}')
print()

# Build row number to row ID map
row_id_map = {}
for row in sheet.get('rows', []):
    row_id_map[row.get('rowNumber')] = row.get('id')

# Define predecessor updates
# Format: row_number: new_predecessor_value
PREDECESSOR_UPDATES = {
    26: '25SS',      # Configure 800 number - parallel with parent
    27: '25SS',      # Set up SIP trunks - parallel with parent (CRITICAL)
    28: '27SS',      # Configure Signal API - parallel to SIP
    29: '27SS',      # Complete queue mapping - parallel to SIP
    30: '27FS',      # Provision DIDs - after SIP trunks
    31: '28FS,30FS', # Validate Screen Pop - after Signal API AND DIDs
}

print('='*80)
print('IGT PREDECESSOR UPDATE PLAN')
print('='*80)
print()
print(f'{"Row":4} | {"Current":15} | {"New":15} | {"Task":40}')
print('-'*80)

# Get current values for display
for row in sheet.get('rows', []):
    row_num = row.get('rowNumber')
    if row_num in PREDECESSOR_UPDATES:
        current_pred = ''
        task_name = ''
        for cell in row.get('cells', []):
            if cell.get('columnId') == pred_col_id:
                current_pred = cell.get('value') or '[NONE]'
            if cell.get('columnId') == col_by_name.get('Tasks'):
                task_name = (cell.get('value') or '')[:40]

        new_pred = PREDECESSOR_UPDATES[row_num]
        print(f'{row_num:4} | {current_pred:15} | {new_pred:15} | {task_name}')

print()

if not EXECUTE:
    print('='*80)
    print('DRY RUN MODE - No changes made')
    print('Set EXECUTE = True to apply changes')
    print('='*80)
else:
    print('='*80)
    print('EXECUTING UPDATES...')
    print('='*80)

    # Build update payload
    rows_to_update = []
    for row_num, new_pred in PREDECESSOR_UPDATES.items():
        row_id = row_id_map.get(row_num)
        if row_id:
            rows_to_update.append({
                'id': row_id,
                'cells': [
                    {
                        'columnId': pred_col_id,
                        'value': new_pred
                    }
                ]
            })

    # Execute update
    update_url = f'https://api.smartsheet.com/2.0/sheets/{TASK_SHEET_ID}/rows'
    response = requests.put(update_url, headers=headers, json=rows_to_update)

    if response.status_code == 200:
        result = response.json()
        print(f'SUCCESS: Updated {len(result.get("result", []))} rows')
        print()
        print('Updated rows:')
        for row in result.get('result', []):
            print(f'  Row ID: {row.get("id")}')
    else:
        print(f'ERROR: {response.status_code}')
        print(json.dumps(response.json(), indent=2))

print()
print(f'Sheet URL: https://app.smartsheet.com/sheets/{TASK_SHEET_ID}')
