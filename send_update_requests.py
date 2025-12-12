"""
Send Update Requests to assignees for their FPS Action Item Log entries
Uses Smartsheet API to create trackable update requests visible in the UI

SAFETY: Validates no duplicates exist before sending to prevent duplicate notifications
"""
import requests
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052

# Column IDs
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_ASSIGNED_TO = 3524234740191108
COL_NOTES = 2961284786769796

# Statuses to EXCLUDE from update requests (already done or not actionable)
EXCLUDED_STATUSES = ['complete', 'completed', 'done', 'cancelled', 'canceled', 'duplicate', 'moved to backlog']

# Duplicate detection threshold
DUPLICATE_THRESHOLD = 0.60

# Columns to include in update request (editable by recipient)
EDITABLE_COLUMNS = [COL_STATUS, COL_NOTES]

# Columns to display for context (read-only)
DISPLAY_COLUMNS = [COL_ACTION_ITEM, COL_STATUS, COL_ASSIGNED_TO, COL_NOTES]

# Name to email mapping for non-email entries
NAME_TO_EMAIL = {
    'Scott Turner': 'c126453@flyfrontier.com',
    'Scott': 'c126453@flyfrontier.com',
    'Hemant Modi': 'hemant.modi@fpsinc.com',
    'Hemant': 'hemant.modi@fpsinc.com',
    'Chirag Handa': 'chirag.handa@fpsinc.com',
    'Chirag': 'chirag.handa@fpsinc.com',
    'Andrew Shaw': 'andrew.shaw@fpsinc.com',
    'Andrew': 'andrew.shaw@fpsinc.com',
    'Angela Dunston': 'Angela.Dunston@flyfrontier.com',
    'Angela': 'Angela.Dunston@flyfrontier.com',
    'Leonardo Declich': 'Leonardo.Declich@flyfrontier.com',
    'Leonardo': 'Leonardo.Declich@flyfrontier.com',
    'Gabe Gunder': 'g.gunder@cognigy.com',
    'Gabe': 'g.gunder@cognigy.com',
    'Joe Pellicano': 'joseph.pellicano@cognigy.nice.com',
    'Joe': 'joseph.pellicano@cognigy.nice.com',
    'Kumar': 'gaurav.kumar2@nice.com',
    'Sandeep': 'sandeep.dhiman@igtsolutions.com',
    'Love Ojha': 'love.ojha@igtsolutions.com',
    'Shiva': 'shiva@igtsolutions.com',
}

# CC recipients on all update requests
CC_RECIPIENTS = [
    'Leonardo.Declich@flyfrontier.com',
    'hemant.modi@fpsinc.com',
    'chirag.handa@fpsinc.com',
]

# Your email (sender) - update this
SENDER_EMAIL = 'c126453@flyfrontier.com'  # Scott

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_sheet_data():
    """Get sheet with rows and identify assignees"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}'
    response = requests.get(url, headers=headers)
    return response.json()

def extract_emails_from_value(value):
    """Extract emails from cell value (handles mixed names and emails)"""
    if not value:
        return []

    emails = set()
    # Split by comma
    parts = [p.strip() for p in str(value).split(',')]

    for part in parts:
        # Check if it's already an email
        if '@' in part:
            emails.add(part.lower())
        # Otherwise look up in name mapping
        elif part in NAME_TO_EMAIL:
            emails.add(NAME_TO_EMAIL[part].lower())

    return list(emails)

def group_rows_by_assignee(sheet):
    """Group row IDs by assignee email, excluding completed rows"""
    assignee_rows = defaultdict(list)
    skipped_completed = 0

    for row in sheet.get('rows', []):
        row_id = row['id']

        # Check status first - skip completed rows
        status = ''
        assignee_value = None
        for cell in row['cells']:
            if cell.get('columnId') == COL_STATUS:
                status = (cell.get('value') or cell.get('displayValue') or '').lower()
            if cell.get('columnId') == COL_ASSIGNED_TO:
                assignee_value = cell.get('value') or cell.get('displayValue')

        # Skip rows with excluded statuses
        if status in EXCLUDED_STATUSES:
            skipped_completed += 1
            continue

        # Add row to assignee's list
        if assignee_value:
            emails = extract_emails_from_value(assignee_value)
            for email in emails:
                if email:
                    assignee_rows[email].append(row_id)

    print(f"Skipped {skipped_completed} rows with Completed/Done status")
    return assignee_rows

def check_for_duplicates(sheet):
    """Check for unmarked duplicates - BLOCKS sending if found

    Checks:
    1. Active items against each other
    2. Active items against completed items (catch re-created tasks)
    """
    active_items = []
    completed_items = []

    for row in sheet.get('rows', []):
        status = ''
        action = ''
        for cell in row.get('cells', []):
            if cell.get('columnId') == COL_STATUS:
                status = (cell.get('value') or '').lower()
            if cell.get('columnId') == COL_ACTION_ITEM:
                action = cell.get('value') or ''

        if action:
            item = {'row': row.get('rowNumber'), 'action': action, 'status': status}
            if status in EXCLUDED_STATUSES:
                if status in ['completed', 'complete', 'done']:
                    completed_items.append(item)
            else:
                active_items.append(item)

    duplicates_found = []

    # PASS 1: Check active items against each other
    for i, item1 in enumerate(active_items):
        for j, item2 in enumerate(active_items):
            if j <= i:
                continue
            ratio = SequenceMatcher(None, item1['action'].lower(), item2['action'].lower()).ratio()
            if ratio >= DUPLICATE_THRESHOLD:
                duplicates_found.append({
                    'row1': item1['row'],
                    'row2': item2['row'],
                    'similarity': f'{ratio:.0%}'
                })

    # PASS 2: Check active items against completed items
    for active in active_items:
        for completed in completed_items:
            ratio = SequenceMatcher(None, active['action'].lower(), completed['action'].lower()).ratio()
            if ratio >= DUPLICATE_THRESHOLD:
                duplicates_found.append({
                    'row1': active['row'],
                    'row2': completed['row'],
                    'similarity': f'{ratio:.0%} (vs COMPLETED)'
                })
                break  # Only flag once per active item

    return duplicates_found

def send_update_request(assignee_email, row_ids):
    """Send update request to a single assignee for their rows"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/updaterequests'

    payload = {
        'sendTo': [{'email': assignee_email}],
        'subject': 'FPS Action Item Status Update Required',
        'message': (
            'Please review and update the status of your assigned action items.\n\n'
            'For each item, please:\n'
            '• Update the Status (New → In Progress → Complete)\n'
            '• Add any notes or resolution details\n\n'
            'Thank you for keeping the project tracker current.'
        ),
        'ccMe': True,
        'rowIds': row_ids,
        'columnIds': DISPLAY_COLUMNS,
        'includeAttachments': True,
        'includeDiscussions': True
    }

    response = requests.post(url, headers=headers, json=payload)
    return response

def main():
    print("Fetching sheet data...")
    sheet = get_sheet_data()

    # SAFETY CHECK: Validate no unmarked duplicates exist
    print("\nValidating no unmarked duplicates...")
    duplicates = check_for_duplicates(sheet)
    if duplicates:
        print("\n" + "=" * 60)
        print("ERROR: UNMARKED DUPLICATES FOUND - ABORTING")
        print("=" * 60)
        print("\nThe following potential duplicates must be resolved first:\n")
        for dup in duplicates:
            print(f"  Row {dup['row1']} and Row {dup['row2']} ({dup['similarity']} similar)")
        print("\nPlease mark duplicates with 'Duplicate' status before sending update requests.")
        print("This prevents sending duplicate notifications to assignees.")
        return

    print("  [OK] No unmarked duplicates found")

    print("\nGrouping rows by assignee...")
    assignee_rows = group_rows_by_assignee(sheet)

    if not assignee_rows:
        print("No assignees found with email addresses.")
        return

    print(f"\nFound {len(assignee_rows)} assignees with action items:")
    for email, rows in assignee_rows.items():
        print(f"  {email}: {len(rows)} items")

    print(f"\nCC recipients: {', '.join(CC_RECIPIENTS)}")
    print("\nSending update requests...")

    success = 0
    errors = 0

    for assignee_email, row_ids in assignee_rows.items():
        # Skip CC recipients from receiving their own update request if they have no items
        if not row_ids:
            continue

        response = send_update_request(assignee_email, row_ids)

        if response.status_code == 200:
            result = response.json()
            request_id = result.get('result', {}).get('id', 'N/A')
            print(f"  [OK] Sent to {assignee_email} ({len(row_ids)} items) - Request ID: {request_id}")
            success += 1
        else:
            print(f"  [ERROR] {assignee_email}: {response.status_code}")
            print(f"    {response.json().get('message', response.text)}")
            errors += 1

    print(f"\nCompleted: {success} sent, {errors} errors")
    print(f"\nUpdate requests are now visible in Smartsheet:")
    print(f"  Sheet > Automation > Update Requests")
    print(f"\nSheet URL: https://app.smartsheet.com/sheets/9W48P8Hm3GrpG7rxMJhHHMjH87Q4rJF3p54qhhC1")

if __name__ == "__main__":
    main()
