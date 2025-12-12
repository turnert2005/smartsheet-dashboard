"""
Complete Predecessor Audit - Raw API Data Analysis
"""
import requests
import json
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

url = f'https://api.smartsheet.com/2.0/sheets/{TASK_SHEET_ID}'
response = requests.get(url, headers=headers)
sheet = response.json()

# Build column map
col_by_name = {col['title']: col['id'] for col in sheet.get('columns', [])}

pred_col_id = col_by_name.get('Predecessors')
task_col_id = col_by_name.get('Tasks')
wbs_col_id = col_by_name.get('WBS')
start_col_id = col_by_name.get('Start Date')
end_col_id = col_by_name.get('End Date')

print('COMPLETE PREDECESSOR AUDIT - RAW API DATA')
print('='*100)
print(f'Predecessors Column ID: {pred_col_id}')
print(f'Total Rows: {len(sheet.get("rows", []))}')
print()

# First pass: identify parent rows (rows that have children)
row_ids_with_children = set()
for row in sheet.get('rows', []):
    parent_id = row.get('parentId')
    if parent_id:
        row_ids_with_children.add(parent_id)

rows_without_pred = []
all_rows_data = []

# Analyze each row
for row in sheet.get('rows', []):
    row_num = row.get('rowNumber')
    row_id = row.get('id')

    wbs = ''
    task = ''
    pred_value = None
    pred_display = None
    start_date = ''
    end_date = ''

    for cell in row.get('cells', []):
        col_id = cell.get('columnId')

        if col_id == wbs_col_id:
            wbs = cell.get('displayValue') or cell.get('value') or ''
        elif col_id == task_col_id:
            task = cell.get('displayValue') or cell.get('value') or ''
        elif col_id == pred_col_id:
            pred_value = cell.get('value')
            pred_display = cell.get('displayValue')
        elif col_id == start_col_id:
            start_date = str(cell.get('value') or '')[:10]
        elif col_id == end_col_id:
            end_date = str(cell.get('value') or '')[:10]

    is_parent = row_id in row_ids_with_children
    has_pred = pred_value is not None and str(pred_value).strip() != ''

    row_data = {
        'row_num': row_num,
        'wbs': wbs,
        'task': task,
        'pred_raw': pred_value,
        'pred_display': pred_display,
        'start_date': start_date,
        'end_date': end_date,
        'is_parent': is_parent,
        'has_pred': has_pred
    }

    all_rows_data.append(row_data)

    if not has_pred:
        rows_without_pred.append(row_data)

# Count categories
parent_count = len([r for r in rows_without_pred if r['is_parent']])
leaf_count = len([r for r in rows_without_pred if not r['is_parent']])

print(f'Rows WITH predecessors: {len(all_rows_data) - len(rows_without_pred)}')
print(f'Rows WITHOUT predecessors: {len(rows_without_pred)}')
print(f'  - PARENT/SUMMARY rows (no predecessor expected): {parent_count}')
print(f'  - LEAF tasks (requires business analysis): {leaf_count}')
print()

print('='*100)
print('CATEGORY 1: PARENT/SUMMARY ROWS')
print('These rows have children - predecessors not needed (dates roll up from children)')
print('='*100)
for r in rows_without_pred:
    if r['is_parent']:
        print(f"Row {r['row_num']:2} | {r['wbs']:8} | {r['task'][:55]}")

print()
print('='*100)
print('CATEGORY 2: LEAF TASKS WITHOUT PREDECESSORS')
print('These are actionable tasks with no predecessor link - requires business analysis')
print('='*100)
print(f"{'Row':4} | {'WBS':8} | {'Task':45} | {'Start':10} | {'End':10}")
print('-'*90)
for r in rows_without_pred:
    if not r['is_parent']:
        print(f"{r['row_num']:4} | {r['wbs']:8} | {r['task'][:45]:45} | {r['start_date']:10} | {r['end_date']:10}")

print()
print('='*100)
print('RAW PREDECESSOR COLUMN VALUES (ALL ROWS)')
print('For verification against Smartsheet UI')
print('='*100)
print(f"{'Row':4} | {'WBS':8} | {'Predecessor Raw':20} | {'Predecessor Display':20}")
print('-'*70)
for r in all_rows_data:
    pred_raw = repr(r['pred_raw']) if r['pred_raw'] else '[None]'
    pred_disp = r['pred_display'] if r['pred_display'] else '[None]'
    print(f"{r['row_num']:4} | {r['wbs']:8} | {pred_raw[:20]:20} | {pred_disp[:20] if pred_disp else '[None]':20}")
