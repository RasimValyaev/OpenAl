import re
from typing import List, Tuple, Optional
from nomenclature_patterns_new import nomenclature_pattern, extract_float
from products import test_products

def find_match(text: str, patterns: List[Tuple]) -> Optional[Tuple[str, int, int]]:
    """Try to match text against a list of patterns and return extracted values."""
    for pattern, handler in patterns:
        match = re.search(pattern, text)  # Using search instead of match to find pattern anywhere in text
        if match:
            try:
                return handler(match)
            except (ValueError, IndexError):
                continue
    return None

def format_result(weight: str, pieces: int, boxes: int) -> str:
    """Format the result string based on the number of parameters."""
    if boxes > 1 and pieces > 1:
        return f"{weight}г x {pieces}box x {boxes}"
    elif boxes > 1:
        return f"{weight}г x {pieces}шт x {boxes}"
    else:
        return f"{weight}г x {pieces}шт"

# Test cases from real data
test_cases = test_products

# Run tests
print("Testing patterns with real data:")
print("-" * 80)
for text in test_cases:
    result = find_match(text, nomenclature_pattern)
    if result:
        weight, pieces, boxes = result
        formatted = format_result(weight, pieces, boxes)
        print(f"✓ {text}")
        print(f"  -> {formatted}")
    else:
        print(f"✗ {text}")
        print("  -> No match")
    print("-" * 80)
