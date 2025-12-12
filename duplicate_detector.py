"""
Enhanced Duplicate Detection for FPS Action Item Log
Uses multi-strategy approach: text similarity + keyword extraction + topic matching

This module prevents duplicate notifications by catching semantically similar items
even when wording differs significantly.
"""
import re
from difflib import SequenceMatcher
from collections import Counter

# Key entities to extract and match on
KEY_ENTITIES = {
    # People
    'angela', 'scott', 'hemant', 'chirag', 'leonardo', 'leo', 'sandeep',
    'love', 'shiva', 'joe', 'jimmy', 'kumar', 'gabe',

    # Technical terms
    'sip trunk', 'sip', 'signal api', 'screen pop', 'azure', 'speech keys',
    'bearer token', 'mongodb', 'cognigy', 'nice', 'cx1', 'cxone',
    'intent', 'uat', 'csg', 'cab', 'arb',

    # Numbers/identifiers
    '800', 'did', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8', 'p9', 'p10',

    # Actions
    'provisioning', 'timeline', 'baseline', 'walkthrough', 'escalate',
    'configuration', 'integration', 'testing', 'routing',

    # Documents
    'project plan', 'action item', 'project schedule', 'documentation'
}

# Multi-word phrases to extract as single entities
PHRASES = [
    'sip trunk', 'signal api', 'screen pop', 'speech keys', 'bearer token',
    'project plan', 'project baseline', 'project schedule', 'action item',
    '800 number', '800 test', 'test number', 'phone number',
    'cab approval', 'arb approval', 'nice cx1', 'nice platform',
    'igt sip', 'azure speech'
]


def extract_key_terms(text):
    """Extract key terms and phrases from action item text"""
    if not text:
        return set()

    text_lower = text.lower()
    terms = set()

    # Extract multi-word phrases first
    for phrase in PHRASES:
        if phrase in text_lower:
            terms.add(phrase)

    # Extract single-word entities
    words = re.findall(r'\b\w+\b', text_lower)
    for word in words:
        if word in KEY_ENTITIES:
            terms.add(word)

    # Extract numbers (like 800)
    numbers = re.findall(r'\b\d{3,}\b', text_lower)
    for num in numbers:
        terms.add(num)

    return terms


def calculate_topic_overlap(terms1, terms2):
    """Calculate overlap score between two sets of key terms"""
    if not terms1 or not terms2:
        return 0.0, 0, set()

    intersection = terms1 & terms2
    union = terms1 | terms2

    # Jaccard similarity
    jaccard = len(intersection) / len(union) if union else 0

    # Also consider absolute overlap count
    overlap_count = len(intersection)

    return jaccard, overlap_count, intersection


def is_semantic_duplicate(item1, item2,
                          similarity_threshold=0.60,
                          high_confidence_threshold=0.75,
                          topic_threshold=0.50,
                          min_shared_terms=3):
    """
    Check if two items are duplicates using multiple strategies.

    Returns: (is_duplicate, reason, confidence)

    Tuned to reduce false positives while catching true duplicates.
    """
    text1 = item1.lower()
    text2 = item2.lower()

    # Strategy 1: High text similarity = definite duplicate
    similarity = SequenceMatcher(None, text1, text2).ratio()
    if similarity >= high_confidence_threshold:
        return True, f"HIGH: text similarity {similarity:.0%}", similarity

    # Strategy 2: Prefix match (first 50 chars)
    if text1[:50] == text2[:50]:
        return True, "HIGH: prefix match", 1.0

    # Strategy 3: Medium similarity + topic overlap = likely duplicate
    terms1 = extract_key_terms(text1)
    terms2 = extract_key_terms(text2)
    jaccard, overlap_count, shared = calculate_topic_overlap(terms1, terms2)

    # Medium similarity (60-75%) + good topic overlap = duplicate
    if similarity >= similarity_threshold and jaccard >= 0.30 and overlap_count >= 2:
        shared_str = ', '.join(list(shared)[:3])
        return True, f"MEDIUM: {similarity:.0%} similar + shared: {shared_str}", similarity

    # Strategy 4: Very high topic overlap = likely duplicate
    # Require higher Jaccard (50%+) and more shared terms (3+) to reduce false positives
    if jaccard >= topic_threshold and overlap_count >= min_shared_terms:
        # Additional check: both should have similar length (within 2x)
        len_ratio = len(text1) / len(text2) if len(text2) > 0 else 0
        if 0.5 <= len_ratio <= 2.0:
            shared_str = ', '.join(list(shared)[:3])
            return True, f"TOPIC: {overlap_count} shared ({jaccard:.0%} Jaccard): {shared_str}", jaccard

    # Strategy 5: Critical term match - specific high-value matches
    # These are terms that when shared usually indicate true duplicates
    critical_matches = shared & {'800 test', '800 number', 'test number', 'azure speech',
                                  'bearer token', 'project baseline', 'cab approval'}
    if critical_matches and overlap_count >= 2:
        return True, f"CRITICAL: {', '.join(critical_matches)}", 0.7

    return False, None, 0.0


def find_all_duplicates(items, existing_items=None):
    """
    Find all duplicates in a list of items.

    Args:
        items: List of dicts with 'action', 'row', 'status' keys
        existing_items: Optional list to check against (for new items)

    Returns: List of duplicate pairs with details
    """
    duplicates = []
    check_against = existing_items if existing_items else items

    for i, item1 in enumerate(items):
        # Skip already handled statuses
        status1 = item1.get('status', '').lower()
        if status1 in ['duplicate', 'completed', 'complete', 'done', 'cancelled', 'canceled', 'moved to backlog']:
            continue

        start_j = 0 if existing_items else i + 1
        for j, item2 in enumerate(check_against[start_j:], start=start_j):
            if existing_items is None and j <= i:
                continue

            # Skip already handled
            status2 = item2.get('status', '').lower()
            if status2 in ['duplicate', 'completed', 'complete', 'done', 'cancelled', 'canceled', 'moved to backlog']:
                continue

            is_dup, reason, confidence = is_semantic_duplicate(
                item1['action'],
                item2['action']
            )

            if is_dup:
                # Determine which is the duplicate (later date = duplicate)
                date1 = item1.get('date', '') or '0000-00-00'
                date2 = item2.get('date', '') or '0000-00-00'

                if date1 <= date2:
                    original, duplicate = item1, item2
                else:
                    original, duplicate = item2, item1

                duplicates.append({
                    'duplicate': duplicate,
                    'original': original,
                    'reason': reason,
                    'confidence': confidence
                })

    return duplicates


def check_new_item(new_action, existing_items):
    """
    Check if a new item would be a duplicate of existing items.

    Args:
        new_action: The action item text
        existing_items: List of existing action texts or dicts

    Returns: (is_duplicate, matching_item, reason)
    """
    for existing in existing_items:
        existing_text = existing if isinstance(existing, str) else existing.get('action', '')

        is_dup, reason, confidence = is_semantic_duplicate(new_action, existing_text)

        if is_dup:
            return True, existing, reason

    return False, None, None


# Test function
def test_detection():
    """Test the duplicate detection with known examples"""
    test_cases = [
        # Should be detected as duplicates
        ("Angela 800 Number and UAT Status - Review Angela email for 800 test number",
         "Confirming the DID count for the 800 test number",
         True),

        ("Azure Speech Keys Testing - Coordinate with cloud team to obtain keys",
         "Azure Speech Keys Testing: Coordinate with the cloud team to obtain keys",
         True),

        ("Project Baseline Update - Update Smartsheet baseline",
         "Project Baseline Update: Update the project baseline in Smartsheet",
         True),

        ("IGT SIP Trunk Timeline Follow-up - Follow up with IGT",
         "IGT SIP Trunk Timeline Confirmation: Follow up with IGT by end of day",
         True),

        # Should NOT be detected as duplicates
        ("Update project schedule with new dates",
         "Send email to team about meeting",
         False),
    ]

    print("DUPLICATE DETECTION TEST")
    print("=" * 70)

    passed = 0
    failed = 0

    for item1, item2, expected in test_cases:
        is_dup, reason, conf = is_semantic_duplicate(item1, item2)
        result = "PASS" if is_dup == expected else "FAIL"

        if result == "PASS":
            passed += 1
        else:
            failed += 1

        print(f"\n[{result}] Expected: {expected}, Got: {is_dup}")
        print(f"  Item 1: {item1[:50]}...")
        print(f"  Item 2: {item2[:50]}...")
        if reason:
            print(f"  Reason: {reason}")

    print(f"\n{'=' * 70}")
    print(f"Results: {passed} passed, {failed} failed")

    return failed == 0


if __name__ == "__main__":
    test_detection()
