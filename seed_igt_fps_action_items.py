"""
Seed FPS Action Item Log with action items from IGT/FPS Daily Go-Live Sync meetings
Uses objectValue format with CONTACT types for proper API compatibility and checks for duplicates
"""
import requests
import json
from datetime import datetime, timedelta
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

# Contact email mapping
CONTACTS = {
    'Kumar': 'gaurav.kumar2@nice.com',
    'Sandeep': 'sandeep.dhiman@igtsolutions.com',
    'Love Ojha': 'love.ojha@igtsolutions.com',
    'Shiva': 'shiva@igtsolutions.com',
    'Angela': 'Angela.Dunston@flyfrontier.com',
    'Hemant': 'hemant.modi@fpsinc.com',
    'Chirag': 'chirag.handa@fpsinc.com',
    'Scott': 'c126453@flyfrontier.com',
    'Leonardo': 'Leonardo.Declich@flyfrontier.com',
    'Joe': 'joseph.pellicano@cognigy.nice.com',
    'Jimmy': 'jimmy.mctiernan@cognigy.nice.com',
}

# Due date rules (business days from date logged)
PRIORITY_DAYS = {
    'Critical': 2,
    'High': 3,
    'Medium': 5,
    'Low': 10
}

COL_OCCURRENCE_COUNT = 7996699210108804

def get_existing_actions():
    """Get existing action items with row IDs for duplicate detection and occurrence counting"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}'
    response = requests.get(url, headers=headers)
    sheet = response.json()

    existing_prefixes = {}  # prefix -> row_id
    existing_full = []  # List of {action, row_id, occurrence_count}

    for row in sheet.get('rows', []):
        row_id = row.get('id')
        action = ''
        occurrence_count = 1

        for cell in row['cells']:
            if cell['columnId'] == COL_ACTION_ITEM:
                action = cell.get('value', '') or ''
            elif cell['columnId'] == COL_OCCURRENCE_COUNT:
                occurrence_count = int(cell.get('value') or 1)

        if action:
            prefix = action[:50].lower()
            existing_prefixes[prefix] = row_id
            existing_full.append({
                'action': action.lower(),
                'row_id': row_id,
                'occurrence_count': occurrence_count
            })

    return existing_prefixes, existing_full


# Critical terms that indicate true duplicates when shared
CRITICAL_TERMS = {
    '800 test', '800 number', 'test number', 'phone number',
    'azure speech', 'speech keys',
    'bearer token',
    'project baseline',
    'cab approval',
    'signal api configuration',
    'sip trunk timeline'
}


def extract_key_terms(text):
    """Extract key terms and phrases from action item text"""
    import re
    if not text:
        return set()

    text_lower = text.lower()
    terms = set()

    # Multi-word phrases
    phrases = [
        'sip trunk', 'signal api', 'screen pop', 'speech keys', 'bearer token',
        'project plan', 'project baseline', 'project schedule', 'action item',
        '800 number', '800 test', 'test number', 'phone number',
        'cab approval', 'arb approval', 'nice cx1', 'nice platform',
        'azure speech', 'signal api configuration', 'sip trunk timeline'
    ]

    for phrase in phrases:
        if phrase in text_lower:
            terms.add(phrase)

    return terms


def is_duplicate(new_action, existing_prefixes, existing_full, threshold=0.75):
    """
    Enhanced duplicate detection using:
    1. Prefix match (first 50 chars)
    2. Text similarity (>75%)
    3. Critical term matching

    Returns: (is_duplicate, reason, matching_row_info)
    matching_row_info contains row_id and occurrence_count if duplicate found
    """
    from difflib import SequenceMatcher

    new_lower = new_action.lower()
    new_prefix = new_lower[:50]

    # Strategy 1: Exact prefix match
    if new_prefix in existing_prefixes:
        row_id = existing_prefixes[new_prefix]
        # Find the full item info
        for item in existing_full:
            if item['row_id'] == row_id:
                return True, "prefix match", item
        return True, "prefix match", {'row_id': row_id, 'occurrence_count': 1}

    # Strategy 2: Text similarity + Critical term matching
    new_terms = extract_key_terms(new_lower)

    for existing in existing_full:
        existing_text = existing['action']

        # Check text similarity
        ratio = SequenceMatcher(None, new_lower, existing_text).ratio()
        if ratio >= threshold:
            return True, f"{ratio:.0%} similar", existing

        # Check critical term overlap (requires 50%+ similarity to avoid false positives)
        existing_terms = extract_key_terms(existing_text)
        shared_critical = (new_terms & existing_terms) & CRITICAL_TERMS

        if shared_critical and ratio >= 0.55:
            return True, f"critical match ({ratio:.0%}): {', '.join(shared_critical)}", existing

    return False, None, None

def add_business_days(start_date, num_days):
    """Add business days to a date (skip weekends)"""
    current = start_date
    days_added = 0
    while days_added < num_days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday=0, Friday=4
            days_added += 1
    return current

def calculate_due_date(date_logged_str, priority='Medium'):
    """Calculate due date based on date logged and priority (business days)"""
    logged = datetime.strptime(date_logged_str, '%Y-%m-%d')
    days_to_add = PRIORITY_DAYS.get(priority, 5)
    due = add_business_days(logged, days_to_add)
    return due.strftime('%Y-%m-%d')

def get_contact_object(assigned_str):
    """Convert assigned names to Smartsheet contact objectValue"""
    names = [n.strip() for n in assigned_str.split(',')]
    contacts = []
    for name in names:
        if name in CONTACTS:
            contacts.append({'objectType': 'CONTACT', 'email': CONTACTS[name]})

    if not contacts:
        return None
    elif len(contacts) == 1:
        return {
            'objectType': 'CONTACT',
            'email': contacts[0]['email']
        }
    else:
        return {
            'objectType': 'MULTI_CONTACT',
            'values': contacts
        }

# Action items from IGT/FPS Daily Go-Live Sync meetings
action_items = [
    # 12/02/2025
    {
        'action': 'Signal API Data Character Limit Confirmation - Confirm max 2019 char limit allocation for AI summary, call ID, intent, skill designation',
        'assigned': 'Kumar',
        'date_logged': '2025-12-02',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Screen Pop Integration for AI Summary - Coordinate with implementation team to integrate and display AI summary in agent screen pop, provide mockup',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-02',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'SIP Trunk Provisioning Timeline - Obtain provisioning dates for staging and production environments from NICE team',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-02',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Critical'
    },
    {
        'action': 'Documentation of Technical Integration Details - Document Cognigy/NICE integration specs (parameters, configuration) and share with stakeholders',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-02',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'Meeting Schedule Update - Send progress updates via email and confirm if next meeting needed or can be replaced by email',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-02',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Low'
    },

    # 12/04/2025
    {
        'action': 'Sharing Test Phone Numbers - Send UAT and production phone numbers to all team members via email',
        'assigned': 'Angela',
        'date_logged': '2025-12-04',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'UAT and Testing Schedule Update - Update project schedule with revised UAT and end-to-end testing dates incorporating CSG timeline',
        'assigned': 'Hemant, Chirag',
        'date_logged': '2025-12-04',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Send CSG dates to Hemant and Chirag for inclusion in updated project schedule',
        'assigned': 'Angela',
        'date_logged': '2025-12-04',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'Signal API and Screen Pop Data Integration - Test integration of AI summary, call ID, intent, skill from Signal API with screen pop using call ID as unique identifier',
        'assigned': 'Sandeep, Shiva',
        'date_logged': '2025-12-04',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Country Code Handling in Call Data - Test calls from different countries to verify ANI/DNIS country code handling works in real-time',
        'assigned': 'Shiva',
        'date_logged': '2025-12-04',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'Internal Team Alignment on Signal API - Reconvene internally to align on Signal API implementation details and be prepared for next meeting',
        'assigned': 'Sandeep, Shiva',
        'date_logged': '2025-12-04',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },

    # 12/05/2025
    {
        'action': 'SIP Trunk Implementation Timeline - Provide exact dates from NICE backend team (2-3 week implementation expected, pushing to ~Christmas)',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-05',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Critical'
    },
    {
        'action': 'Signal API and Screen Pop Data Integration - Share scope document with NICE, Joe, Angela outlining requirements including call type and skill IDs',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-05',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Signal API Technical Support Coordination - Bridge Joe, Angela, Scott, Hemant into NICE email thread for full context on Signal API implementation',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-05',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Test Phone Numbers for UAT - Share test phone numbers with team once UAT ready to begin',
        'assigned': 'Angela',
        'date_logged': '2025-12-05',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'Agent Handoff Walkthrough Scheduling - Schedule NICE platform walkthrough with Raymond as presenter for all relevant participants',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-05',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'Project Timeline Review Process - Prepare and present updated project timeline at beginning of future calls for visibility',
        'assigned': 'Chirag',
        'date_logged': '2025-12-05',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },

    # 12/09/2025
    {
        'action': 'SIP Trunk Provisioning ETA - Escalate and obtain precise date (not range) for SIP trunk completion; project is ~15 days behind due to this blocker',
        'assigned': 'Love Ojha, Sandeep',
        'date_logged': '2025-12-09',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Critical'
    },
    {
        'action': 'SIP Refer Confirmation - Confirm IGT is performing SIP refer lookups when receiving transferred calls from CSG using new transfer number',
        'assigned': 'Love Ojha, Sandeep',
        'date_logged': '2025-12-09',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Signal API Data Requirements - Clarify which Signal API parameters (P1-P10) for HTML data, plain text, routing info; determine scripting ownership',
        'assigned': 'Love Ojha, Sandeep',
        'date_logged': '2025-12-09',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'NICE CX1 Walkthrough Scheduling - Schedule and conduct walkthrough session of NICE CX1 for the team',
        'assigned': 'Love Ojha',
        'date_logged': '2025-12-09',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },

    # 12/10/2025 - IGT/FPS Daily Sync
    {
        'action': 'SIP Trunk Timeline from NICE - Obtain exact timeline for SIP trunk provisioning, forward email to group, ask NICE if expediting possible',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-10',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Critical'
    },
    {
        'action': 'SIP Trunk Dec 23 Date Validation - Update group on whether Dec 23 date for SIP trunk readiness is still realistic after NICE clarification',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-10',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Signal API Resource Alignment - Coordinate with NICE to bring Jimmy onto technical call to finalize Signal API integration details',
        'assigned': 'Sandeep, Joe',
        'date_logged': '2025-12-10',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Technical Integration Documentation - Work with Jimmy to provide detailed SIP and Signal API parameters documentation for Frontier and ARB',
        'assigned': 'Joe',
        'date_logged': '2025-12-10',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'NICE Platform Walkthrough - Schedule walkthrough with Raymond for 8 AM MT Thursday, send meeting invite to group',
        'assigned': 'Sandeep, Leonardo',
        'date_logged': '2025-12-10',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },

    # 12/10/2025 - FPS Daily Sync
    {
        'action': 'Project Baseline Update - Update Smartsheet baseline to reflect Jan 13 start date and intent V2 inclusion',
        'assigned': 'Scott',
        'date_logged': '2025-12-10',
        'meeting': 'FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'Azure Speech Keys Testing - Coordinate with cloud team to obtain and validate test Azure STT/TTS keys for Cognigy integration',
        'assigned': 'Hemant, Scott, Leonardo',
        'date_logged': '2025-12-10',
        'meeting': 'FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Angela 800 Number and UAT Status - Review Angela email for 800 test number and UAT/staging progress updates, clarify outstanding items',
        'assigned': 'Chirag',
        'date_logged': '2025-12-10',
        'meeting': 'FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'IGT SIP Trunk Timeline Follow-up - Follow up with IGT by end of week to confirm SIP trunk timeline after NICE update, adjust schedule as needed',
        'assigned': 'Leonardo',
        'date_logged': '2025-12-10',
        'meeting': 'FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Signal API Configuration Assignment - Update project plan to accurately assign Signal API configuration responsibility for Cognigy and NICE CX1 sides',
        'assigned': 'Hemant, Chirag',
        'date_logged': '2025-12-10',
        'meeting': 'FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'CAB Approval Scheduling Note - Add note to project plan that CAB meetings occur Mon/Thu and schedule based on deployment date',
        'assigned': 'Scott',
        'date_logged': '2025-12-10',
        'meeting': 'FPS Daily Sync',
        'priority': 'Low'
    },
    {
        'action': 'Project Plan Review Process - Ensure both project timeline and action item log are reviewed in all IGT/partner calls for visibility',
        'assigned': 'Scott, Hemant, Chirag',
        'date_logged': '2025-12-10',
        'meeting': 'FPS Daily Sync',
        'priority': 'Medium'
    },

    # 12/11/2025 - IGT/FPS Daily Sync
    {
        'action': 'SIP Trunk Provisioning Timeline Confirmation - Validate specific holidays and non-working days affecting 15 business day timeline, provide final end-to-end provisioning date',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-11',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Critical'
    },
    {
        'action': 'SIP Trunk Timeline Escalation - Escalate with NICE team to reduce provisioning from 15 to 7-10 business days as previously communicated, confirm if expedited timeline possible',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-11',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Critical'
    },
    {
        'action': 'Signal API Configuration Timeline - Coordinate with NICE to determine timeline for configuring Signal API on CX1 after SIP trunk, confirm if can be done in parallel',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-11',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Bearer Token Procurement for Signal API - Confirm with NICE whether bearer token for Signal API has been requested, initiate process if not',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-11',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
    {
        'action': 'Inclusion of NICE Team in Project Calls - Ensure appropriate NICE team members (SIP trunk and Signal API) are included in future calls to clarify requirements',
        'assigned': 'Sandeep',
        'date_logged': '2025-12-11',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'Medium'
    },
    {
        'action': 'Provision of NICE Implementation Scripts - Send sample NICE scripting templates (SIP trunk and Signal API integration) to all project participants',
        'assigned': 'Jimmy',
        'date_logged': '2025-12-11',
        'meeting': 'IGT/FPS Daily Sync',
        'priority': 'High'
    },
]

def main():
    # Check for existing items to avoid duplicates
    print("Checking for existing action items...")
    existing_prefixes, existing_full = get_existing_actions()
    print(f"Found {len(existing_full)} existing items in sheet")

    # Track new rows and rows to update (increment occurrence)
    new_rows = []
    rows_to_update = []  # {row_id, new_count}
    updated_row_ids = set()  # Prevent double-counting same row

    for item in action_items:
        # Check for duplicate using multiple strategies
        is_dup, reason, match_info = is_duplicate(item['action'], existing_prefixes, existing_full)

        if is_dup and match_info:
            row_id = match_info['row_id']

            # Only increment each row once per run
            if row_id not in updated_row_ids:
                current_count = match_info.get('occurrence_count', 1)
                new_count = current_count + 1
                rows_to_update.append({
                    'row_id': row_id,
                    'new_count': new_count,
                    'action': item['action'][:50],
                    'meeting': item.get('meeting', 'Meeting'),
                    'date_logged': item.get('date_logged', 'Unknown')
                })
                updated_row_ids.add(row_id)
                print(f"  INCREMENT ({reason}): {item['action'][:50]}... (count: {current_count} -> {new_count})")
            else:
                print(f"  SKIP (already counted): {item['action'][:50]}...")
            continue

        # New item - add with occurrence count = 1
        due_date = calculate_due_date(item['date_logged'], item['priority'])
        contact_obj = get_contact_object(item['assigned'])

        cells = [
            {'columnId': COL_ACTION_ITEM, 'objectValue': item['action']},
            {'columnId': COL_STATUS, 'objectValue': 'New'},
            {'columnId': COL_DUE_DATE, 'value': due_date},
            {'columnId': COL_PRIORITY, 'objectValue': item['priority']},
            {'columnId': COL_MEETING_SOURCE, 'objectValue': item['meeting']},
            {'columnId': COL_DATE_LOGGED, 'value': item['date_logged']},
            {'columnId': COL_OCCURRENCE_COUNT, 'value': 1}  # Initialize count
        ]

        if contact_obj:
            cells.append({'columnId': COL_ASSIGNED_TO, 'objectValue': contact_obj})

        new_rows.append({
            'toBottom': True,
            'cells': cells
        })

    # Update occurrence counts for existing items with recurrence comments
    if rows_to_update:
        print(f"\nUpdating occurrence counts for {len(rows_to_update)} existing items...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        update_payload = []
        for row in rows_to_update:
            # Add comment documenting the recurrence
            meeting_source = row.get('meeting', 'Meeting')
            date_logged = row.get('date_logged', 'Unknown date')
            comment = f"[{timestamp}] Recurrence from {meeting_source} ({date_logged})"

            update_payload.append({
                'id': row['row_id'],
                'cells': [
                    {'columnId': COL_OCCURRENCE_COUNT, 'value': row['new_count']},
                    {'columnId': COL_NOTES, 'value': comment}
                ]
            })

        update_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
        response = requests.put(update_url, headers=headers, json=update_payload)

        if response.status_code == 200:
            print(f"  [OK] Updated {len(rows_to_update)} occurrence counts")
        else:
            print(f"  [ERROR] Failed to update: {response.status_code}")
            print(response.text)

    # Add new rows
    if new_rows:
        print(f"\nAdding {len(new_rows)} new action items...")
        url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
        response = requests.post(url, headers=headers, json=new_rows)

        result = response.json()
        if response.status_code == 200:
            print(f'  [OK] Added {len(result.get("result", []))} new items!')
        else:
            print(f'  [ERROR] {response.status_code}')
            print(json.dumps(result, indent=2))
    else:
        print(f"\nNo new items to add")

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(new_rows)} new, {len(rows_to_update)} incremented")
    print(f"{'='*60}")
    print(f'Sheet URL: https://app.smartsheet.com/sheets/9W48P8Hm3GrpG7rxMJhHHMjH87Q4rJF3p54qhhC1')

if __name__ == "__main__":
    main()
