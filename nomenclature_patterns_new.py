import re
import locale

# Set locale once at module level
locale.setlocale(locale.LC_ALL, "")
DECIMAL_POINT = locale.localeconv()["decimal_point"]

# Pre-compile common patterns
UNITS = r"(?:г|гр|грам|gram|g|gr|G|GR)"
NUMBER = r"(\d+(?:[.,]\d+)?)"
SEPARATOR = r"[*xXхХ]"
PIECES = r"(?:шт|шт\.|\s*box)"
BLOCKS = r"(?:бл|блок|блоков)"

def extract_float(text: str) -> float:
    """Convert string to float handling different decimal separators."""
    return float(text.replace(",", DECIMAL_POINT).replace(".", DECIMAL_POINT))

def process_match(weight: float, pieces: int, boxes: int = 1) -> tuple:
    """Process matches to handle special cases."""
    if boxes > 1 and pieces > 1:
        # If we have both pieces and boxes > 1, treat pieces as boxes
        return weight, pieces, boxes
    return weight, pieces, boxes

# Main pattern list with optimized patterns for product descriptions
nomenclature_pattern = [
    # Pattern for pieces and blocks without separator (20шт Х 4бл)
    (
        rf'.*?(\d+)\s*{UNITS}\s+.*?(\d+)\s*шт\s*{SEPARATOR}\s*(\d+)\s*{BLOCKS}(?:\s+|$)',
        lambda m: process_match(extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Basic pattern with weight and pieces (290г*12шт)
    (
        rf'.*?{NUMBER}\s*{UNITS}\s*{SEPARATOR}\s*(\d+){PIECES}?(?:\s+|$|№|/)',
        lambda m: process_match(extract_float(m.group(1)), int(m.group(2))),
    ),
    
    # Pattern with weight, pieces and blocks (19гр.Х 24 Х 6)
    (
        rf'.*?{NUMBER}\s*{UNITS}\.?\s*{SEPARATOR}\s*(\d+)\s*{SEPARATOR}\s*(\d+)(?:\s+|$|№)',
        lambda m: process_match(extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    
    # Pattern with pieces, weight and blocks (100шт 500гр Х12)
    (
        rf'.*?(\d+)\s*шт\s*{NUMBER}\s*{UNITS}\s*{SEPARATOR}\s*(\d+)(?:\s+|$|№)',
        lambda m: process_match(extract_float(m.group(2)), int(m.group(1)), int(m.group(3))),
    ),
    
    # Pattern with weight and pieces followed by blocks (25 гр 24Х6бл)
    (
        rf'.*?{NUMBER}\s*{UNITS}\s*(\d+)\s*{SEPARATOR}\s*(\d+)\s*{BLOCKS}(?:\s+|$|№)',
        lambda m: process_match(extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    
    # Pattern with weight and pieces, followed by text (350 г х 12 шт)
    (
        rf'.*?{NUMBER}\s*{UNITS}\s*{SEPARATOR}\s*(\d+)\s*{PIECES}(?:\s+|$|№)',
        lambda m: process_match(extract_float(m.group(1)), int(m.group(2))),
    ),
    
    # Pattern with weight and pieces, decimal weight (2,5 г 200 шт Х 12)
    (
        rf'.*?{NUMBER}\s*{UNITS}\s*(\d+)\s*{PIECES}\s*{SEPARATOR}\s*(\d+)(?:\s+|$|№)',
        lambda m: process_match(extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
]