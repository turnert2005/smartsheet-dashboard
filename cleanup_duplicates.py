"""
Duplicate Cleanup Script for FPS Action Item Log
Identifies, reviews, and marks duplicates to prevent duplicate notifications

Run modes:
  --scan     : Scan and display duplicates (default, safe)
  --mark     : Mark identified duplicates with 'Duplicate' status
  --delete   : Delete duplicate rows (use with caution)

Usage:
  python cleanup_duplicates.py --scan
  python cleanup_duplicates.py --mark
"""
import requests
import json
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052

# Column IDs
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_DATE_LOGGED = 7464884414140292
COL_NOTES = 2961284786769796
COL_ASSIGNED_TO = 3524234740191108

# Statuses already excluded (don't re-check these)
ALREADY_HANDLED = ['duplicate', 'completed', 'complete', 'done', 'cancelled', 'canceled', 'moved to backlog']

# Similarity threshold for duplicate detection
DUPLICATE_THRESHOLD = 0.75

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

# Multi-word phrases to extract
KEY_PHRASES = [
    'sip trunk', 'signal api', 'screen pop', 'speech keys', 'bearer token',
    'project plan', 'project baseline', 'project schedule', 'action item',
    '800 number', '800 test', 'test number', 'phone number',
    'cab approval', 'arb approval', 'nice cx1', 'nice platform',
    'azure speech', 'signal api configuration', 'sip trunk timeline'
]


def extract_key_terms(text):
    """Extract key terms and phrases from action item text"""
    if not text:
        return set()
    text_lower = text.lower()
    terms = set()
    for phrase in KEY_PHRASES:
        if phrase in text_lower:
            terms.add(phrase)
    return terms

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_sheet_data():
    """Fetch sheet with all row data"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}'
    response = requests.get(url, headers=headers)
    return response.json()

def extract_items(sheet):
    """Extract action items with metadata"""
    items = []
    for row in sheet.get('rows', []):
        row_id = row['id']
        row_num = row.get('rowNumber')
        action = ''
        status = ''
        date_logged = ''
        assigned = ''

        for cell in row.get('cells', []):
            col_id = cell.get('columnId')
            if col_id == COL_ACTION_ITEM:
                action = cell.get('value', '') or ''
            elif col_id == COL_STATUS:
                status = cell.get('value', '') or ''
            elif col_id == COL_DATE_LOGGED:
                date_logged = cell.get('value', '') or ''
            elif col_id == COL_ASSIGNED_TO:
                assigned = cell.get('displayValue', '') or ''

        if action:
            items.append({
                'row_id': row_id,
                'row': row_num,
                'action': action,
                'status': status,
                'date': date_logged,
                'assigned': assigned
            })

    return items

def check_pair_is_duplicate(text1, text2):
    """Check if two action texts are duplicates. Returns (is_dup, reason, similarity)"""
    is_dup = False
    reason = ''

    # Strategy 1: High text similarity (>75%)
    ratio = SequenceMatcher(None, text1, text2).ratio()
    if ratio >= DUPLICATE_THRESHOLD:
        is_dup = True
        reason = f'{ratio:.0%} similar'

    # Strategy 2: Prefix match
    elif text1[:50] == text2[:50]:
        is_dup = True
        reason = 'prefix match'
        ratio = 1.0

    # Strategy 3: Critical term matching (requires 55%+ similarity)
    else:
        terms1 = extract_key_terms(text1)
        terms2 = extract_key_terms(text2)
        shared_critical = (terms1 & terms2) & CRITICAL_TERMS

        if shared_critical and ratio >= 0.55:
            is_dup = True
            reason = f"critical ({ratio:.0%}): {', '.join(shared_critical)}"

    return is_dup, reason, ratio


def find_duplicates(items):
    """Find all duplicate pairs using enhanced detection with critical term matching"""
    duplicates = []

    # Separate active and completed items
    active_items = [i for i in items if i['status'].lower() not in ALREADY_HANDLED]
    completed_items = [i for i in items if i['status'].lower() in ['completed', 'complete', 'done']]

    # Track which items are duplicates (to avoid marking same item multiple times)
    duplicate_row_ids = set()

    # PASS 1: Check active items against each other
    for i, item1 in enumerate(active_items):
        if item1['row_id'] in duplicate_row_ids:
            continue

        for j, item2 in enumerate(active_items):
            if j <= i or item2['row_id'] in duplicate_row_ids:
                continue

            text1 = item1['action'].lower()
            text2 = item2['action'].lower()

            is_dup, reason, _ = check_pair_is_duplicate(text1, text2)

            if is_dup:
                # Determine which is the duplicate (later date = duplicate)
                date1 = item1['date'] or '0000-00-00'
                date2 = item2['date'] or '0000-00-00'

                if date1 <= date2:
                    original = item1
                    duplicate = item2
                else:
                    original = item2
                    duplicate = item1

                duplicate_row_ids.add(duplicate['row_id'])
                duplicates.append({
                    'duplicate': duplicate,
                    'original': original,
                    'reason': reason
                })

    # PASS 2: Check active items against completed items (catch "re-opened" duplicates)
    for active in active_items:
        if active['row_id'] in duplicate_row_ids:
            continue

        for completed in completed_items:
            text1 = active['action'].lower()
            text2 = completed['action'].lower()

            is_dup, reason, _ = check_pair_is_duplicate(text1, text2)

            if is_dup:
                # Active item duplicates a completed one - active is the duplicate
                duplicate_row_ids.add(active['row_id'])
                duplicates.append({
                    'duplicate': active,
                    'original': completed,
                    'reason': f'{reason} (of COMPLETED item)'
                })
                break  # Only flag once per active item

    return duplicates

def scan_duplicates():
    """Scan and display all duplicates"""
    print("=" * 70)
    print("DUPLICATE SCAN - FPS Action Item Log")
    print("=" * 70)
    print()

    print("Fetching sheet data...")
    sheet = get_sheet_data()
    items = extract_items(sheet)

    print(f"Total items: {len(items)}")

    # Count by status
    status_counts = defaultdict(int)
    for item in items:
        status_counts[item['status'] or '[Empty]'] += 1

    print("\nStatus distribution:")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        handled = "(already handled)" if status.lower() in ALREADY_HANDLED else ""
        print(f"  {status:20} {count:3} {handled}")

    print("\nScanning for duplicates...")
    duplicates = find_duplicates(items)

    if not duplicates:
        print("\n" + "=" * 70)
        print("[OK] NO DUPLICATES FOUND - Sheet is clean!")
        print("=" * 70)
        return []

    print(f"\n[WARNING] Found {len(duplicates)} duplicate(s):\n")

    for idx, dup in enumerate(duplicates, 1):
        d = dup['duplicate']
        o = dup['original']
        reason = dup.get('reason', 'match')

        print(f"--- Duplicate #{idx} ({reason}) ---")
        print(f"  KEEP (Row {o['row']:2}, {o['date']}): {o['action'][:70]}...")
        print(f"  MARK (Row {d['row']:2}, {d['date']}): {d['action'][:70]}...")
        print()

    print("=" * 70)
    print(f"SUMMARY: {len(duplicates)} duplicate(s) found")
    print("Run with --mark to mark them as 'Duplicate' status")
    print("=" * 70)

    return duplicates

def mark_duplicates():
    """Mark all duplicates with 'Duplicate' status"""
    print("=" * 70)
    print("MARKING DUPLICATES - FPS Action Item Log")
    print("=" * 70)
    print()

    print("Fetching sheet data...")
    sheet = get_sheet_data()
    items = extract_items(sheet)

    print("Finding duplicates...")
    duplicates = find_duplicates(items)

    if not duplicates:
        print("\n[OK] No duplicates to mark - sheet is clean!")
        return

    print(f"\nMarking {len(duplicates)} duplicate(s)...")

    # Build update payload
    rows_to_update = []
    for dup in duplicates:
        d = dup['duplicate']
        o = dup['original']

        rows_to_update.append({
            'id': d['row_id'],
            'cells': [
                {'columnId': COL_STATUS, 'value': 'Duplicate'},
                {'columnId': COL_NOTES, 'value': f"Duplicate of Row {o['row']} (logged {o['date']})"}
            ]
        })

    # Update in batches if needed
    update_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows'
    response = requests.put(update_url, headers=headers, json=rows_to_update)

    if response.status_code == 200:
        print("\n" + "=" * 70)
        print(f"[SUCCESS] Marked {len(duplicates)} row(s) as Duplicate")
        print("=" * 70)
        print("\nRows marked:")
        for dup in duplicates:
            d = dup['duplicate']
            o = dup['original']
            print(f"  Row {d['row']} -> Duplicate (of Row {o['row']})")
    else:
        print(f"\n[ERROR] Failed to update: {response.status_code}")
        print(response.json())

def cleanup_duplicates():
    """Find and delete duplicate rows automatically (no confirmation)"""
    print("=" * 70)
    print("CLEANUP DUPLICATES - FPS Action Item Log")
    print("=" * 70)
    print()

    print("Fetching sheet data...")
    sheet = get_sheet_data()
    items = extract_items(sheet)

    print("Finding duplicates...")
    duplicates = find_duplicates(items)

    if not duplicates:
        print("\n[OK] No duplicates found - sheet is clean!")
        return 0

    print(f"\nFound {len(duplicates)} duplicate(s):")
    for dup in duplicates:
        d = dup['duplicate']
        o = dup['original']
        reason = dup.get('reason', 'match')
        print(f"  Row {d['row']} ({reason}) -> duplicate of Row {o['row']}")

    # Delete rows
    row_ids = [dup['duplicate']['row_id'] for dup in duplicates]
    delete_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows?ids={",".join(map(str, row_ids))}'
    response = requests.delete(delete_url, headers=headers)

    if response.status_code == 200:
        print(f"\n[OK] Deleted {len(duplicates)} duplicate row(s)")
        return len(duplicates)
    else:
        print(f"\n[ERROR] Failed to delete: {response.status_code}")
        print(response.json())
        return -1


def delete_duplicates():
    """Delete duplicate rows (with confirmation prompt)"""
    print("=" * 70)
    print("DELETE DUPLICATES - FPS Action Item Log")
    print("=" * 70)
    print()
    print("[WARNING] This will permanently delete rows!")
    print()

    print("Fetching sheet data...")
    sheet = get_sheet_data()
    items = extract_items(sheet)

    print("Finding duplicates...")
    duplicates = find_duplicates(items)

    if not duplicates:
        print("\n[OK] No duplicates to delete - sheet is clean!")
        return

    print(f"\nFound {len(duplicates)} duplicate(s) to delete:")
    for dup in duplicates:
        d = dup['duplicate']
        print(f"  Row {d['row']}: {d['action'][:60]}...")

    # Confirm deletion
    confirm = input("\nType 'DELETE' to confirm deletion: ")
    if confirm != 'DELETE':
        print("Aborted - no rows deleted")
        return

    # Delete rows
    row_ids = [dup['duplicate']['row_id'] for dup in duplicates]
    delete_url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows?ids={",".join(map(str, row_ids))}'
    response = requests.delete(delete_url, headers=headers)

    if response.status_code == 200:
        print(f"\n[SUCCESS] Deleted {len(duplicates)} duplicate row(s)")
    else:
        print(f"\n[ERROR] Failed to delete: {response.status_code}")
        print(response.json())

def main():
    mode = '--cleanup'  # Default: auto-delete duplicates
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    if mode == '--scan':
        scan_duplicates()
    elif mode == '--mark':
        mark_duplicates()
    elif mode == '--cleanup':
        cleanup_duplicates()
    elif mode == '--delete':
        delete_duplicates()
    else:
        print("Usage:")
        print("  python cleanup_duplicates.py --cleanup (default - find and delete duplicates)")
        print("  python cleanup_duplicates.py --scan    (scan only - show duplicates without action)")
        print("  python cleanup_duplicates.py --mark    (mark duplicates with 'Duplicate' status)")
        print("  python cleanup_duplicates.py --delete  (delete with confirmation prompt)")

if __name__ == "__main__":
    main()
