"""
Update FPS Action Item Log with proper contacts and due dates
"""
import requests
import json
from datetime import datetime, timedelta
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052

# Column IDs
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_ASSIGNED_TO = 3524234740191108
COL_DUE_DATE = 8027834367561604
COL_PRIORITY = 709484973084548
COL_MEETING_SOURCE = 5213084600455044
COL_NOTES = 2961284786769796
COL_DATE_LOGGED = 7464884414140292

# Contact email mapping
CONTACTS = {
    'Scott': 'c126453@flyfrontier.com',
    'Hemant': 'hemant.modi@fpsinc.com',
    'Chirag': 'chirag.handa@fpsinc.com',
    'Andrew': 'andrew.shaw@fpsinc.com',
    'Angela': 'Angela.Dunston@flyfrontier.com',
    'Leonardo': 'Leonardo.Declich@flyfrontier.com',
    'Gabe': 'g.gunder@cognigy.com',
    'Joe': 'joseph.pellicano@cognigy.nice.com',
}

# Due date rules (business days from date logged)
PRIORITY_DAYS = {
    'High': 2,
    'Medium': 5,
    'Low': 10
}

def add_business_days(start_date, num_days):
    """Add business days to a date (skip weekends)"""
    current = start_date
    days_added = 0
    while days_added < num_days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday=0, Friday=4
            days_added += 1
    return current

def parse_assignees(notes_value):
    """Extract assignee names from notes field"""
    if not notes_value or not notes_value.startswith('Assigned:'):
        return []
    names_str = notes_value.replace('Assigned:', '').strip()
    names = [n.strip() for n in names_str.split(',')]
    return names

def get_contact_objects(names):
    """Convert names to Smartsheet contact objects"""
    contacts = []
    for name in names:
        if name in CONTACTS:
            contacts.append({'email': CONTACTS[name]})
    return contacts

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

# Get current sheet data
url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}'
response = requests.get(url, headers=headers)
sheet = response.json()

# Build update rows
update_rows = []

for row in sheet['rows']:
    row_id = row['id']

    # Get current values
    notes_val = None
    date_logged_val = None
    priority_val = None

    for cell in row['cells']:
        col_id = cell.get('columnId')
        if col_id == COL_NOTES:
            notes_val = cell.get('value')
        elif col_id == COL_DATE_LOGGED:
            date_logged_val = cell.get('value')
        elif col_id == COL_PRIORITY:
            priority_val = cell.get('value')

    # Build update cells
    cells = []

    # Update Assigned To with contact objects
    if notes_val:
        names = parse_assignees(notes_val)
        contacts = get_contact_objects(names)
        if contacts:
            if len(contacts) == 1:
                cells.append({
                    'columnId': COL_ASSIGNED_TO,
                    'objectValue': {
                        'objectType': 'CONTACT',
                        'email': contacts[0]['email']
                    }
                })
            else:
                cells.append({
                    'columnId': COL_ASSIGNED_TO,
                    'objectValue': {
                        'objectType': 'MULTI_CONTACT',
                        'values': [{'objectType': 'CONTACT', 'email': c['email']} for c in contacts]
                    }
                })

    # Calculate and set due date
    if date_logged_val and priority_val:
        date_logged = datetime.strptime(date_logged_val, '%Y-%m-%d')
        days_to_add = PRIORITY_DAYS.get(priority_val, 5)
        due_date = add_business_days(date_logged, days_to_add)
        cells.append({
            'columnId': COL_DUE_DATE,
            'value': due_date.strftime('%Y-%m-%d')
        })

    # Clear the notes field (assignees now in proper column)
    cells.append({
        'columnId': COL_NOTES,
        'value': ''
    })

    if cells:
        update_rows.append({
            'id': row_id,
            'cells': cells
        })

# Update rows in batches
url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
response = requests.put(url, headers=headers, json=update_rows)

if response.status_code == 200:
    result = response.json()
    print(f'Successfully updated {len(result.get("result", []))} rows!')
    print(f'\nDue date rules applied:')
    print(f'  High priority: 2 business days from date logged')
    print(f'  Medium priority: 5 business days from date logged')
    print(f'  Low priority: 10 business days from date logged')
    print(f'\nSheet URL: https://app.smartsheet.com/sheets/9W48P8Hm3GrpG7rxMJhHHMjH87Q4rJF3p54qhhC1')
else:
    print(f'Error: {response.status_code}')
    print(json.dumps(response.json(), indent=2))
