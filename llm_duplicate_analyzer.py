"""
LLM-Enhanced Duplicate Detection using Claude 4.5 Opus
Three-layer approach: Logic + Keywords + Semantic Analysis

This module provides:
1. Semantic duplicate detection using Claude API
2. Occurrence count tracking (increment vs create new)
3. Full sheet validation
"""
import os
import json
import requests
from difflib import SequenceMatcher
from anthropic import Anthropic

# Smartsheet and Anthropic config
from config import SMARTSHEET_API_TOKEN, ANTHROPIC_API_KEY

# Initialize Anthropic client
client = None

def get_client():
    global client
    if client is None:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return client

SHEET_ID = 4528757755826052
COL_ACTION_ITEM = 1272434926505860
COL_STATUS = 5776034553876356
COL_DATE_LOGGED = 7464884414140292
COL_NOTES = 2961284786769796
COL_OCCURRENCE_COUNT = 7996699210108804

EXCLUDED_STATUSES = ['duplicate', 'completed', 'complete', 'done', 'cancelled', 'canceled', 'moved to backlog']

headers = {
    'Authorization': f'Bearer {SMARTSHEET_API_TOKEN}',
    'Content-Type': 'application/json'
}


def get_sheet_data():
    """Fetch sheet with all row data"""
    url = f'https://api.smartsheet.com/2.0/sheets/{SHEET_ID}'
    response = requests.get(url, headers=headers)
    return response.json()


def extract_key_terms(text):
    """Extract key terms for quick filtering"""
    if not text:
        return set()

    text_lower = text.lower()
    terms = set()

    phrases = [
        'sip trunk', 'signal api', 'screen pop', 'speech keys', 'bearer token',
        'project plan', 'project baseline', 'project schedule',
        '800 number', '800 test', 'test number', 'phone number',
        'cab approval', 'arb approval', 'nice cx1', 'azure speech',
        'sip trunk timeline', 'signal api configuration'
    ]

    for phrase in phrases:
        if phrase in text_lower:
            terms.add(phrase)

    return terms


def quick_duplicate_check(item1, item2):
    """
    Layer 1 & 2: Quick logic-based check before LLM analysis.
    Returns: (is_likely_duplicate, confidence, reason)
    """
    text1 = item1.lower()
    text2 = item2.lower()

    # Layer 1: High text similarity
    similarity = SequenceMatcher(None, text1, text2).ratio()
    if similarity >= 0.80:
        return True, similarity, f"high_similarity:{similarity:.0%}"

    # Layer 1: Prefix match
    if text1[:50] == text2[:50]:
        return True, 1.0, "prefix_match"

    # Layer 2: Critical term overlap
    terms1 = extract_key_terms(text1)
    terms2 = extract_key_terms(text2)

    critical_terms = {
        '800 test', '800 number', 'test number', 'azure speech',
        'bearer token', 'project baseline', 'cab approval'
    }

    shared_critical = (terms1 & terms2) & critical_terms
    if shared_critical:
        return True, 0.7, f"critical_terms:{','.join(shared_critical)}"

    # Medium similarity - needs LLM verification
    if similarity >= 0.50:
        return None, similarity, "needs_llm_verification"

    # Low similarity but shared terms - needs LLM verification
    shared = terms1 & terms2
    if len(shared) >= 2:
        return None, 0.4, f"shared_terms:{','.join(shared)}"

    return False, 0, "no_match"


def llm_analyze_pair(item1, item2, context1="", context2=""):
    """
    Layer 3: Use Claude 4.5 Opus to semantically analyze if two items are duplicates.

    Returns: {
        'is_duplicate': bool,
        'confidence': float (0-1),
        'reasoning': str,
        'recommendation': 'mark_duplicate' | 'keep_both' | 'merge'
    }
    """
    prompt = f"""You are analyzing action items from a project tracker to determine if they are duplicates.

Two items are duplicates if they represent THE SAME TASK or REQUEST, even if worded differently.
Items are NOT duplicates if they are RELATED but represent DIFFERENT ACTIONS (e.g., "get timeline" vs "escalate timeline").

ITEM 1:
{item1}
{f"Context: {context1}" if context1 else ""}

ITEM 2:
{item2}
{f"Context: {context2}" if context2 else ""}

Analyze these items and respond in JSON format:
{{
    "is_duplicate": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why these are/aren't duplicates",
    "recommendation": "mark_duplicate" | "keep_both" | "merge",
    "suggested_merged_text": "If merge recommended, provide combined text"
}}

Key considerations:
- Same topic but different actions = NOT duplicate (e.g., "review document" vs "send document")
- Same request with different wording = DUPLICATE
- Follow-up on same item = might be duplicate (check if new info added)
- Slight variations in phrasing = DUPLICATE"""

    try:
        response = get_client().messages.create(
            model="claude-sonnet-4-20250514",  # Using Sonnet for cost efficiency, can upgrade to Opus
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON from response
        response_text = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()

        result = json.loads(json_str)
        return result

    except Exception as e:
        print(f"  LLM analysis error: {e}")
        return {
            'is_duplicate': False,
            'confidence': 0,
            'reasoning': f"Error: {str(e)}",
            'recommendation': 'keep_both'
        }


def analyze_pair_full(item1, item2, use_llm=True):
    """
    Full three-layer analysis of two items.

    Returns: {
        'is_duplicate': bool,
        'confidence': float,
        'method': str,
        'reasoning': str,
        'recommendation': str
    }
    """
    # Layers 1 & 2: Quick check
    quick_result, confidence, reason = quick_duplicate_check(item1, item2)

    if quick_result is True:
        return {
            'is_duplicate': True,
            'confidence': confidence,
            'method': 'logic',
            'reasoning': reason,
            'recommendation': 'mark_duplicate'
        }

    if quick_result is False:
        return {
            'is_duplicate': False,
            'confidence': 0,
            'method': 'logic',
            'reasoning': reason,
            'recommendation': 'keep_both'
        }

    # Layer 3: LLM analysis for uncertain cases
    if use_llm:
        llm_result = llm_analyze_pair(item1, item2)
        return {
            'is_duplicate': llm_result.get('is_duplicate', False),
            'confidence': llm_result.get('confidence', 0),
            'method': 'llm',
            'reasoning': llm_result.get('reasoning', ''),
            'recommendation': llm_result.get('recommendation', 'keep_both')
        }

    # If LLM disabled, be conservative
    return {
        'is_duplicate': False,
        'confidence': confidence,
        'method': 'logic_uncertain',
        'reasoning': reason,
        'recommendation': 'review_manually'
    }


def validate_all_rows(use_llm=True, batch_size=10):
    """
    Validate ALL rows in sheet for duplicates using three-layer analysis.

    Returns comprehensive report of all duplicate pairs found.
    """
    print("=" * 70)
    print("FULL SHEET VALIDATION - Three-Layer Duplicate Analysis")
    print("=" * 70)
    print()

    print("Fetching sheet data...")
    sheet = get_sheet_data()

    # Extract items
    items = []
    for row in sheet.get('rows', []):
        action = ''
        status = ''
        date = ''
        row_id = row.get('id')
        row_num = row.get('rowNumber')

        for cell in row.get('cells', []):
            col_id = cell.get('columnId')
            if col_id == COL_ACTION_ITEM:
                action = cell.get('value', '') or ''
            elif col_id == COL_STATUS:
                status = cell.get('value', '') or ''
            elif col_id == COL_DATE_LOGGED:
                date = cell.get('value', '') or ''

        if action:
            items.append({
                'row': row_num,
                'row_id': row_id,
                'action': action,
                'status': status,
                'date': date
            })

    print(f"Total items: {len(items)}")

    # Filter active items
    active_items = [i for i in items if i['status'].lower() not in EXCLUDED_STATUSES]
    print(f"Active items to check: {len(active_items)}")
    print()

    # Find duplicates
    duplicates = []
    checked_pairs = set()
    llm_calls = 0

    print("Analyzing pairs...")

    for i, item1 in enumerate(active_items):
        for j, item2 in enumerate(active_items):
            if j <= i:
                continue

            pair_key = (item1['row_id'], item2['row_id'])
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            # Full analysis
            result = analyze_pair_full(item1['action'], item2['action'], use_llm=use_llm)

            if result['method'] == 'llm':
                llm_calls += 1

            if result['is_duplicate']:
                # Determine original (earlier date)
                date1 = item1['date'] or '0000'
                date2 = item2['date'] or '0000'

                if date1 <= date2:
                    original, duplicate = item1, item2
                else:
                    original, duplicate = item2, item1

                duplicates.append({
                    'original': original,
                    'duplicate': duplicate,
                    'confidence': result['confidence'],
                    'method': result['method'],
                    'reasoning': result['reasoning'],
                    'recommendation': result['recommendation']
                })

                print(f"  [{result['method'].upper()}] Row {duplicate['row']} is duplicate of Row {original['row']}")
                print(f"    Confidence: {result['confidence']:.0%}")
                print(f"    Reason: {result['reasoning'][:60]}...")
                print()

    # Summary
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total pairs checked: {len(checked_pairs)}")
    print(f"LLM calls made: {llm_calls}")
    print(f"Duplicates found: {len(duplicates)}")
    print()

    if duplicates:
        print("DUPLICATES TO RESOLVE:")
        print("-" * 70)

        # Group by method
        logic_dups = [d for d in duplicates if d['method'] == 'logic']
        llm_dups = [d for d in duplicates if d['method'] == 'llm']

        if logic_dups:
            print(f"\nHIGH CONFIDENCE (Logic-based): {len(logic_dups)}")
            for d in logic_dups:
                print(f"  Row {d['duplicate']['row']} -> duplicate of Row {d['original']['row']}")
                print(f"    {d['duplicate']['action'][:60]}...")

        if llm_dups:
            print(f"\nLLM VERIFIED: {len(llm_dups)}")
            for d in llm_dups:
                print(f"  Row {d['duplicate']['row']} -> duplicate of Row {d['original']['row']} ({d['confidence']:.0%})")
                print(f"    {d['reasoning'][:60]}...")
    else:
        print("[OK] No duplicates found - sheet is clean!")

    return duplicates


def check_new_item_against_existing(new_action, existing_items, use_llm=True):
    """
    Check if a new item would be a duplicate of any existing item.
    Used before adding new rows.

    Returns: {
        'is_duplicate': bool,
        'matching_row': row info or None,
        'confidence': float,
        'recommendation': 'add_new' | 'increment_count' | 'skip'
    }
    """
    for existing in existing_items:
        result = analyze_pair_full(new_action, existing['action'], use_llm=use_llm)

        if result['is_duplicate']:
            return {
                'is_duplicate': True,
                'matching_row': existing,
                'confidence': result['confidence'],
                'reasoning': result['reasoning'],
                'recommendation': 'increment_count'
            }

    return {
        'is_duplicate': False,
        'matching_row': None,
        'confidence': 0,
        'recommendation': 'add_new'
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--no-llm':
        print("Running without LLM (logic-only mode)")
        validate_all_rows(use_llm=False)
    else:
        print("Running with LLM analysis (Claude)")
        validate_all_rows(use_llm=True)
