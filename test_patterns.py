import re
import time
from typing import List, Tuple, Optional

# Import both pattern sets
from nomenclature_extract_pattern import nomenclature_pattern as original_patterns
from nomenclature_extract_pattern_optimized import nomenclature_pattern as optimized_patterns

def find_match(text: str, patterns: List[Tuple]) -> Optional[Tuple[float, int, int]]:
    """Try to match text against a list of patterns and return extracted values."""
    for pattern, handler in patterns:
        match = re.match(pattern, text)
        if match:
            try:
                return handler(match)
            except (ValueError, IndexError):
                continue
    return None

def test_patterns(test_cases: List[str], patterns: List[Tuple], name: str) -> Tuple[int, float]:
    """Test a pattern set against test cases and return success count and time."""
    start_time = time.time()
    successes = 0
    
    print(f"\nTesting {name}:")
    for text in test_cases:
        result = find_match(text, patterns)
        if result:
            print(f"✓ {text} -> {result}")
            successes += 1
        else:
            print(f"✗ {text} -> No match")
    
    elapsed = time.time() - start_time
    return successes, elapsed

# Test cases covering various formats
test_cases = [
    "16g*24pcs*12boxes",  # Basic format with *
    "6GR*6*12",  # Format with GR
    "16g24pcs12boxes",  # Format without separators
    "500g 500G x 8Boxes",  # Format with weight at start and end
    "3,5 GX24X8",  # Format with decimal
    "12,5 гр 20 Х 30 бл",  # Format with Cyrillic
    "10X48X28G",  # Format with dimensions
    "100g x 8 pcs x 12tray",  # Format with units
    "900grx6",  # Format with weight and count
    "6KT24AD30G CIS2",  # Format with KT/AD
    "12SP 184G(CS)",  # Format with SP
    "24PK 90G",  # Format with PK
    "40 грамХ12штХ2бл Kenton",  # Format with Cyrillic units
    "22 г * 24 шт* 6 бл",  # Format with Cyrillic and *
]

# Run tests
orig_success, orig_time = test_patterns(test_cases, original_patterns, "Original Patterns")
opt_success, opt_time = test_patterns(test_cases, optimized_patterns, "Optimized Patterns")

# Print summary
print("\nSummary:")
print(f"Original: {orig_success}/{len(test_cases)} matches in {orig_time:.3f}s")
print(f"Optimized: {opt_success}/{len(test_cases)} matches in {opt_time:.3f}s")
print(f"Time improvement: {((orig_time - opt_time) / orig_time * 100):.1f}%")