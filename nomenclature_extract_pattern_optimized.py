import re
import locale

# Set locale once at module level
locale.setlocale(locale.LC_ALL, "")
DECIMAL_POINT = locale.localeconv()["decimal_point"]

# Pre-compile common patterns
UNITS = r"(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)"
PCS = r"(?:pcs|pc|шт|p)"
BOXES = r"(?:boxes|box|jars|jar|tray|trays|vase|vases|bag|bags|бл|блок|блоков)"
NUMBER = r"(\d+(?:[.,]\d+)?)"
SEPARATOR = r"[*xXхХ×]"

def extract_float(text: str) -> float:
    """Convert string to float handling different decimal separators."""
    return float(text.replace(",", DECIMAL_POINT).replace(".", DECIMAL_POINT))

# Main pattern list with optimized and consolidated patterns
nomenclature_pattern = [
    # Format with * (16g*24pcs*12boxes)
    (
        rf"{NUMBER}\s*{UNITS}\s*{SEPARATOR}\s*(\d+)(?:\s*{PCS})?\s*{SEPARATOR}\s*(\d+)",
        lambda m: (extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Format with weight and units (KT/AD/G formats consolidated)
    (
        rf"(\d+)\s*KT\s*(\d+)\s*AD[T]?\s*{NUMBER}\s*G(?:\s*[A-Z/]+|\s*\([A-Z.-]+\))?",
        lambda m: (extract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Format with SP/PK and weight
    (
        rf"(\d+)\s*(?:SP|PK)\s*{NUMBER}\s*G(?:\s*[A-Z]+|\s*\([A-Z]+\))?",
        lambda m: (extract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Format without separators
    (
        rf"{NUMBER}{UNITS}(\d+){PCS}?(\d+){BOXES}",
        lambda m: (extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Format with weight at start and end
    (
        rf"(?:^|\s){NUMBER}\s*{UNITS}.*?(\d+)\s*{UNITS}\s*{SEPARATOR}\s*(\d+)(?:\s|{BOXES}|$)",
        lambda m: (extract_float(m.group(2)), 1, int(m.group(3))),
    ),
    # Format with decimal weight
    (
        rf"{NUMBER}\s*{UNITS}{SEPARATOR}\s*(\d+){SEPARATOR}\s*(\d+)",
        lambda m: (extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Format with dimensions
    (
        rf"(\d+)\s*{SEPARATOR}\s*(\d+)\s*{SEPARATOR}\s*{NUMBER}\s*{UNITS}(?:\s|$)",
        lambda m: (extract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Format with weight and count
    (
        rf"{NUMBER}\s*{UNITS}{SEPARATOR}\s*(\d+)(?:\s|$)",
        lambda m: (extract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Format with units and blocks
    (
        rf"{NUMBER}\s*{UNITS}\s*(\d+)\s*{BOXES}\s*{SEPARATOR}\s*(\d+)\s*{PCS}",
        lambda m: (extract_float(m.group(1)), int(m.group(3)), int(m.group(2))),
    ),
    # Format with Cyrillic units and blocks
    (
        rf"{NUMBER}\s*(?:г|гр|грам|грамм)\s+(\d+)\s*(?:шт|штХ|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Format with Cyrillic units and asterisk
    (
        rf"{NUMBER}\s*(?:г|гр|грам|грамм)\s*[*]\s*(\d+)\s*(?:шт|штХ|шт\s*[*])\s*[*]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (extract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Format with repeated weight
    (
        rf"{NUMBER}\s*{UNITS}\s+{NUMBER}\s*{UNITS}\s*{SEPARATOR}\s*(\d+)\s*{BOXES}",
        lambda m: (extract_float(m.group(2)), 1, int(m.group(3))),
    ),
]