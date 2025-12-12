"""
Assignee Analysis - Check all rows by assignee for duplicates and sanity
Also investigates strikethrough formatting
"""
import requests
from collections import defaultdict
from difflib import SequenceMatcher
from config import SMARTSHEET_API_TOKEN

SHEET_ID = 4528757755826052

# Column IDs
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_ASSIGNED_TO = 3524234740191108
COL_DATE_LOGGED = 7464884414140292
COL_OCCURRENCE_COUNT = 7996699210108804

EXCLUDED_STATUSES = ['duplicate', 'completed', 'complete', 'done', 'cancelled', 'canceled', 'moved to backlog']

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_sheet_data():
    """Fetch sheet with all row data including format"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}?include=format'
    response = requests.get(url, headers=headers)
    return response.json()

def extract_row_data(sheet):
    """Extract all rows with full metadata"""
    rows = []
    for row in sheet.get('rows', []):
        row_id = row.get('id')
        row_num = row.get('rowNumber')
        row_format = row.get('format', '')

        action = ''
        status = ''
        assigned = ''
        date_logged = ''
        occurrence = 1
        has_strikethrough = False

        for cell in row.get('cells', []):
            col_id = cell.get('columnId')
            cell_format = cell.get('format', '')

            if col_id == COL_ACTION_ITEM:
                action = cell.get('value', '') or ''
                # Check for strikethrough (format position 5 = "1")
                if cell_format:
                    parts = cell_format.split(',')
                    if len(parts) > 5 and parts[5] == '1':
                        has_strikethrough = True
            elif col_id == COL_STATUS:
                status = cell.get('value', '') or ''
            elif col_id == COL_ASSIGNED_TO:
                assigned = cell.get('displayValue', '') or cell.get('value', '') or ''
            elif col_id == COL_DATE_LOGGED:
                date_logged = cell.get('value', '') or ''
            elif col_id == COL_OCCURRENCE_COUNT:
                occurrence = cell.get('value', 1) or 1

        if action:
            rows.append({
                'row': row_num,
                'row_id': row_id,
                'action': action,
                'status': status,
                'assigned': assigned,
                'date': date_logged,
                'occurrence': occurrence,
                'strikethrough': has_strikethrough
            })

    return rows

def analyze_by_assignee(rows, target_assignee=None):
    """Group and analyze rows by assignee"""
    by_assignee = defaultdict(list)

    for row in rows:
        assigned = row['assigned']
        if assigned:
            # Handle multi-contact - split by comma
            for name in assigned.split(','):
                name = name.strip()
                if name:
                    by_assignee[name].append(row)

    return by_assignee

def check_duplicates_within_group(items, threshold=0.55):
    """Check for potential duplicates within a group of items"""
    duplicates = []
    active = [i for i in items if i['status'].lower() not in EXCLUDED_STATUSES]

    for i, item1 in enumerate(active):
        for j, item2 in enumerate(active):
            if j <= i:
                continue

            text1 = item1['action'].lower()
            text2 = item2['action'].lower()
            ratio = SequenceMatcher(None, text1, text2).ratio()

            if ratio >= threshold:
                duplicates.append({
                    'row1': item1['row'],
                    'row2': item2['row'],
                    'action1': item1['action'][:60],
                    'action2': item2['action'][:60],
                    'similarity': ratio
                })

    return duplicates

def analyze_specific_pair(rows, row1_num, row2_num):
    """Analyze a specific pair of rows"""
    item1 = None
    item2 = None

    for row in rows:
        if row['row'] == row1_num:
            item1 = row
        elif row['row'] == row2_num:
            item2 = row

    if not item1 or not item2:
        return None

    text1 = item1['action'].lower()
    text2 = item2['action'].lower()
    ratio = SequenceMatcher(None, text1, text2).ratio()

    return {
        'item1': item1,
        'item2': item2,
        'similarity': ratio
    }

def main():
    print("=" * 80)
    print("ASSIGNEE ANALYSIS - FPS Action Item Log")
    print("=" * 80)
    print()

    print("Fetching sheet data...")
    sheet = get_sheet_data()
    rows = extract_row_data(sheet)

    print(f"Total rows: {len(rows)}")

    # Find strikethroughs
    strikethrough_rows = [r for r in rows if r['strikethrough']]
    print(f"Rows with strikethrough: {len(strikethrough_rows)}")

    if strikethrough_rows:
        print("\n--- STRIKETHROUGH ROWS ---")
        for r in strikethrough_rows:
            print(f"  Row {r['row']:2}: [{r['status']}] {r['action'][:70]}...")

    # Group by assignee
    by_assignee = analyze_by_assignee(rows)

    print(f"\n{'=' * 80}")
    print("ANALYSIS BY ASSIGNEE")
    print("=" * 80)

    for assignee in sorted(by_assignee.keys()):
        items = by_assignee[assignee]
        active = [i for i in items if i['status'].lower() not in EXCLUDED_STATUSES]

        print(f"\n--- {assignee} ({len(active)} active / {len(items)} total) ---")

        # List active items
        for item in active:
            strike = "[STRIKE]" if item['strikethrough'] else ""
            occ = f"(x{int(item['occurrence'])})" if item['occurrence'] > 1 else ""
            print(f"  Row {item['row']:2} {strike}{occ}: {item['action'][:65]}...")

        # Check for duplicates within this assignee's items
        dups = check_duplicates_within_group(items)
        if dups:
            print(f"\n  [!] POTENTIAL DUPLICATES for {assignee}:")
            for d in dups:
                print(f"      Row {d['row1']} vs Row {d['row2']} ({d['similarity']:.0%} similar)")

    # Specific analysis: Rows 38 and 44 (Chirag's concern)
    print(f"\n{'=' * 80}")
    print("CHIRAG'S CONCERN: Rows 38 and 44")
    print("=" * 80)

    pair = analyze_specific_pair(rows, 38, 44)
    if pair:
        print(f"\nRow 38: {pair['item1']['action']}")
        print(f"  Status: {pair['item1']['status']}")
        print(f"  Assigned: {pair['item1']['assigned']}")
        print(f"  Date: {pair['item1']['date']}")
        print(f"  Strikethrough: {pair['item1']['strikethrough']}")

        print(f"\nRow 44: {pair['item2']['action']}")
        print(f"  Status: {pair['item2']['status']}")
        print(f"  Assigned: {pair['item2']['assigned']}")
        print(f"  Date: {pair['item2']['date']}")
        print(f"  Strikethrough: {pair['item2']['strikethrough']}")

        print(f"\nSimilarity: {pair['similarity']:.0%}")

        # Semantic analysis
        if pair['similarity'] >= 0.55:
            print("\n[!] These ARE flagged as potential duplicates by our logic (>55% similar)")
        else:
            print("\n[OK] These are NOT flagged as duplicates by our logic (<55% similar)")
            print("     They appear to be related but DIFFERENT action items")
    else:
        print("Could not find both rows 38 and 44")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"Total assignees: {len(by_assignee)}")
    print(f"Rows with strikethrough: {len(strikethrough_rows)}")

    # Count total potential duplicates
    all_dups = []
    for assignee in by_assignee:
        dups = check_duplicates_within_group(by_assignee[assignee])
        all_dups.extend(dups)

    print(f"Potential duplicate pairs across all assignees: {len(all_dups)}")

if __name__ == "__main__":
    main()
