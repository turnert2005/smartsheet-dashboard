"""
Seed FPS Action Item Log with action items from meeting notes
"""
import requests
import json
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

# Column IDs
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_ASSIGNED_TO = 3524234740191108
COL_DUE_DATE = 8027834367561604
COL_PRIORITY = 709484973084548
COL_MEETING_SOURCE = 5213084600455044
COL_NOTES = 2961284786769796
COL_DATE_LOGGED = 7464884414140292
COL_RELATED_TICKET = 1835384879927172

# Action items from meetings
action_items = [
    # 12/02/2025 - Daily Standup
    {
        'action': 'Resolve Hemant access issue to Smartsheet - resend invite or troubleshoot authentication',
        'assigned': 'Scott, Hemant',
        'date_logged': '2025-12-02',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Follow up with Leo and IGT to confirm and document SIP trunk procurement approval',
        'assigned': 'Scott, Angela',
        'date_logged': '2025-12-02',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Coordinate with Jimmy and JP for technical setup documentation/walkthrough (SIP trunks, signal API, voice gateway)',
        'assigned': 'Gabe',
        'date_logged': '2025-12-02',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Send ARB feedback/thoughts to Scott for architecture design documentation',
        'assigned': 'Hemant, Chirag',
        'date_logged': '2025-12-02',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },

    # 12/04/2025 - Daily Standup
    {
        'action': 'Update Smartsheet Project Schedule with all details and updated dates',
        'assigned': 'Chirag',
        'date_logged': '2025-12-04',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Reply to IGT email thread to clarify SIP trunk approval and 12-month commitment terms; consult James on showstopper status',
        'assigned': 'Leonardo',
        'date_logged': '2025-12-04',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Provide layman outline explaining current and new intent definition solutions for non-technical stakeholders',
        'assigned': 'Andrew',
        'date_logged': '2025-12-04',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },

    # 12/05/2025 - Daily Standup
    {
        'action': 'Manually replicate detailed project plan data into existing Smartsheet (single source of truth)',
        'assigned': 'Chirag',
        'date_logged': '2025-12-05',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Update SIP trunk estimated completion date in Smartsheet with comment based on IGT feedback',
        'assigned': 'Chirag',
        'date_logged': '2025-12-05',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Iterate on intent update documentation to make it less technical and more accessible',
        'assigned': 'Scott, Andrew',
        'date_logged': '2025-12-05',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Prepare and schedule live demo of voice bot for team review next week',
        'assigned': 'Andrew',
        'date_logged': '2025-12-05',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Add recent operational backlog items (incorrect follow-up, missing input field) to Smartsheet and monitor',
        'assigned': 'Chirag',
        'date_logged': '2025-12-05',
        'meeting': 'Daily Standup',
        'priority': 'Low'
    },
    {
        'action': 'Review incorrect follow-up message ticket; determine if fix can be pushed alongside intent taxonomy update',
        'assigned': 'Andrew',
        'date_logged': '2025-12-05',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },

    # 12/08/2025 - Daily Standup
    {
        'action': 'Update project plan with all dependencies (predecessors) and adjust downstream dates for SIP trunk delay impact',
        'assigned': 'Chirag',
        'date_logged': '2025-12-08',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Populate project task sheet with all required data - statuses and baseline start dates; mark completed subtasks',
        'assigned': 'Chirag',
        'date_logged': '2025-12-08',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Follow up with Sandeep for IGT SIP trunk provisioning status update',
        'assigned': 'Hemant',
        'date_logged': '2025-12-08',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Incorporate CSG timeline from Angela into project plan with current accurate dates',
        'assigned': 'Chirag',
        'date_logged': '2025-12-08',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Send updated MongoDB config to Scott (clarify prod vs lower environment discrepancies)',
        'assigned': 'Andrew',
        'date_logged': '2025-12-08',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Compile and send remaining ARB information for Cognigy to Scott',
        'assigned': 'Joe',
        'date_logged': '2025-12-08',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Complete intent QA review and deploy to UAT; provide results to Scott',
        'assigned': 'Andrew',
        'date_logged': '2025-12-08',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },

    # 12/09/2025 - Daily Standup
    {
        'action': 'Complete intent QA review, deploy to UAT, and share results with Scott',
        'assigned': 'Andrew',
        'date_logged': '2025-12-09',
        'meeting': 'Daily Standup',
        'priority': 'High'
    },
    {
        'action': 'Share QA test cases being used for intent validation with Scott',
        'assigned': 'Chirag',
        'date_logged': '2025-12-09',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Update project plan baseline to reflect intent V2 deployment shift (Jan 7 to Jan 13)',
        'assigned': 'Hemant',
        'date_logged': '2025-12-09',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    },
    {
        'action': 'Rename task from "Integrate Knowledge Owl" to "Validate Knowledge Owl" in project plan',
        'assigned': 'Hemant',
        'date_logged': '2025-12-09',
        'meeting': 'Daily Standup',
        'priority': 'Low'
    },
    {
        'action': 'Mark "Provision production APIs" task as complete (validation done)',
        'assigned': 'Hemant',
        'date_logged': '2025-12-09',
        'meeting': 'Daily Standup',
        'priority': 'Low'
    },
    {
        'action': 'Mark "Secure Architecture Review Board Approval" and parent task as In Progress',
        'assigned': 'Chirag',
        'date_logged': '2025-12-09',
        'meeting': 'Daily Standup',
        'priority': 'Low'
    },
    {
        'action': 'Mark all CSG UAT-related items as In Progress; aim to complete UAT by end of week',
        'assigned': 'Chirag',
        'date_logged': '2025-12-09',
        'meeting': 'Daily Standup',
        'priority': 'Medium'
    }
]

# Build rows - Note: Assigned To stored in Notes column since Contact List requires valid Smartsheet contacts
rows = []
for item in action_items:
    row = {
        'toBottom': True,
        'cells': [
            {'columnId': COL_ACTION_ITEM, 'value': item['action']},
            {'columnId': COL_STATUS, 'value': 'New'},
            {'columnId': COL_NOTES, 'value': f"Assigned: {item['assigned']}"},
            {'columnId': COL_PRIORITY, 'value': item['priority']},
            {'columnId': COL_MEETING_SOURCE, 'value': item['meeting']},
            {'columnId': COL_DATE_LOGGED, 'value': item['date_logged']}
        ]
    }
    rows.append(row)

# Add rows to sheet
url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
response = requests.post(url, headers=headers, json=rows)

result = response.json()
if response.status_code == 200:
    print(f'Successfully added {len(result.get("result", []))} action items!')
    print(f'\nSheet URL: https://app.smartsheet.com/sheets/9W48P8Hm3GrpG7rxMJhHHMjH87Q4rJF3p54qhhC1')
else:
    print(f'Error: {response.status_code}')
    print(json.dumps(result, indent=2))
