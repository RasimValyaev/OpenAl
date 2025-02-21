import re
import locale

# Set locale once at module level
locale.setlocale(locale.LC_ALL, "")
DECIMAL_POINT = locale.localeconv()["decimal_point"]

# Pre-compile common patterns
UNITS = r"(?:г|гр|грам|грамм|gram|g|gr|G|GR)"
NUMBER = r"(\d+(?:[.,]\d+)?)"
SEPARATOR = r"(?:\*|x|X|х|Х])" # r"[*xXхХ]"
PIECES = r"(?:шт|штук|pcs|ad|adt|adet|)"
BLOCKS = r"(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|кт|box|boxes)"


def extract_float(text: str) -> float:
    """Convert string to float handling different decimal separators."""
    return text.replace(",", DECIMAL_POINT).replace(".", DECIMAL_POINT)


def process_match(weight: str, pieces: int, boxes: int = 1) -> tuple:
    """Process matches to handle special cases."""
    if boxes > 1 and pieces > 1:
        # If we have both pieces and boxes > 1, treat pieces as boxes
        return weight, pieces, boxes
    return weight, pieces, boxes


nomenclature_pattern = [
    # "COKOKREM" шоколадная паста 180г*6шт № 00061-00
    (
        rf".*?(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gram|g|gr|G|GR)(?:\.)?\s*(?:\*|x|X|х|Х])\s*(\d+)\s*(?:шт|штук|pcs|ad|adet)(?:\s+|$)",
        lambda m: process_match(extract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Яйце шоколадне "BARBELLA WORLD " з іграшкою в середині 25 гр 24Х6бл
    (
        rf".*?(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gram|g|gr|G|GR)\s*(\d+)\s*[*xXхХ]\s*(\d+)(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|кт|box|boxes)(?:\s+|$)",
        lambda m: process_match(
            extract_float(m.group(1)), int(m.group(2)), int(m.group(3))
        ),
    ),
]
