"""
Attach meeting notes files to corresponding rows in FPS Action Item Log
"""
import requests
import os
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052
DATE_LOGGED_COL = 7464884414140292

# Map dates to file names
DATE_TO_FILE = {
    '2025-12-02': 'Meeting-Notes/AI-Meeting-Notes-FPS-Daily-Go-Live-Sync_12022025.docx',
    '2025-12-04': 'Meeting-Notes/AI-Meeting-Notes-FPS-Daily-Go-Live-Sync_12042025.docx',
    '2025-12-05': 'Meeting-Notes/AI-Meeting-Notes-FPS-Daily-Go-Live-Sync_12052025.docx',
    '2025-12-08': 'Meeting-Notes/AI-Meeting-Notes-FPS-Daily-Go-Live-Sync_12082025.docx',
    '2025-12-09': 'Meeting-Notes/AI-Meeting-Notes-FPS-Daily-Go-Live-Sync_12092025.docx',
}

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
}

# Get sheet with rows
url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}'
response = requests.get(url, headers={**headers, 'Content-Type': 'application/json'})
sheet = response.json()

# Track which files have been attached to which rows
attachments_made = 0
errors = 0

for row in sheet['rows']:
    row_id = row['id']
    date_val = None

    for cell in row['cells']:
        if cell.get('columnId') == DATE_LOGGED_COL and cell.get('value'):
            date_val = cell['value']
            break

    if date_val and date_val in DATE_TO_FILE:
        file_path = DATE_TO_FILE[date_val]

        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)

            # Attach file to row
            attach_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows/{row_id}/attachments'

            with open(file_path, 'rb') as f:
                file_data = f.read()

            attach_headers = {
                'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'Content-Disposition': f'attachment; filename="{file_name}"',
                'Content-Length': str(len(file_data))
            }

            response = requests.post(attach_url, headers=attach_headers, data=file_data)

            if response.status_code == 200:
                attachments_made += 1
                print(f'Attached {file_name} to row {row_id}')
            else:
                errors += 1
                print(f'Error attaching to row {row_id}: {response.status_code} - {response.text}')

print(f'\nCompleted: {attachments_made} attachments made, {errors} errors')
print(f'Sheet URL: https://app.smartsheet.com/sheets/9W48P8Hm3GrpG7rxMJhHHMjH87Q4rJF3p54qhhC1')
