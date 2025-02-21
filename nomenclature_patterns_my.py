import re
import locale

# Set locale once at module level
locale.setlocale(locale.LC_ALL, "")
DECIMAL_POINT = locale.localeconv()["decimal_point"]

# Pre-compile common patterns
UNITS = r"(?:грамм|грам|гр|г|gram|grm|gr|g|ml)"
NUMBER = r"(\d+(?:[.,]\d+)?)"
SEPARATOR = r"(?:\*|×|х|Х|x|X])?"
PIECES = r"(?:штук|шт|pcs|adet|adt|ad|sp|pkt|pk)"
BLOCKS = r"(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kutu|kt)"


def extract_float(text: str) -> str:
    """Convert string to float handling different decimal separators."""
    return text.replace(",", DECIMAL_POINT).replace(".", DECIMAL_POINT)


def process_match(weight: str, pieces: int, boxes: int = 1) -> tuple:
    return weight, pieces, boxes


nomenclature_pattern = [
    #2. LOLLIPOP MAXXI WATERMELON 10X48X28G; 6kt 24ad 42 CIS2
    (
        rf"(\d+)\s*(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kutu|kt)\s*(?:\*|×|х|Х|x|X|X])?\s*(\d+)\s*(?:штук|шт|pcs|adet|adt|ad|sp|pkt|pk)?(?:\*|×|х|Х|x|X|X])?\s*(\d+(?:[.,]\d+)?)\s*(?:грамм|грам|гр|г|gram|grm|gr|g|ml)?(?:\s+|$)",
        lambda m: process_match(
            extract_float(m.group(3)), int(m.group(2)), int(m.group(1))
        ),
    ),
    #1. OZMO HOPPO CIK. 4kt*12adt*40g
    (
        rf"(\d+)(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kutu|kt)\s*(?:\*|×|х|Х|x|X])?\s*(\d+)\s*(?:штук|шт|pcs|adet|adt|ad|sp|pkt|pk)\s*(?:\*|×|х|Х|x|X])?(\d+[.,]?\d*)\s*(?:грамм|грам|гр|г|gram|grm|gr|g|ml)(?:.|\s+|$)",
        lambda m: process_match(
            extract_float(m.group(3)), int(m.group(2)), int(m.group(1))
        ),
    ),
    #5. Ice Cream Lolly Marshmallow 12gx30pcsx24boxes
    (
        rf"(\d+[.,]?\d*)(?:грамм|грам|гр|г|gram|grm|gr|g|ml)\s*.*?\s*(\d+)\s*(?:штук|шт|pcs|adet|adt|ad|sp|pkt|pk)\s*(?:\*|×|х|Х|x|X])?\s*(\d+)\s*(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kt)(?:\s+|$)",
        lambda m: process_match(
            extract_float(extract_float(m.group(1))), int(m.group(2)), int(m.group(3))
        ),
    ),
    #6. Печ.сах. "Лора" с маршмаллоу со вкусом клубники глазированное 30г*60шт №302
    # 500g Macaron Cookies (Mixed Flavors) 500gx 8boxes
    # 30г*60шт
    # 160гр х24
    # 205гр Х 12шт; 300 гр Х 12 шт; 290,25г*12шт
    (
        rf".*?(\d+(?:[.,]\d+)?)\s*(?:грамм|грам|гр|г|gram|grm|gr|g|ml)\s*(?:\*|×|х|Х|x|X])?\s*(\d+)\s*(?:штук|шт|pcs|adet|adt|ad|sp|бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kutu|kt)(?:\s+|$)",
        lambda m: process_match(extract_float(m.group(1)), 1, int(m.group(2))),
    ),
    #4. Печиво "Simley " сендвіч з маршмеллоу покрите глазур'ю 19гр.Х 24 Х 6
    (
        rf"(\d+[.,]?\d*)(?:грамм|грам|гр|г|gram|grm|gr|g|ml)\.*(?:\*|×|х|Х|x|X])?\s*(\d+)\s*(?:штук|шт|pcs|adet|adt|ad|sp|pkt|pk)?\s*(?:\*|×|х|Х|x|X])?\s*(\d+)(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kt)?",
        lambda m: process_match(
            extract_float(extract_float(m.group(1))), int(m.group(3)), int(m.group(2))
        ),
    ),
    #3. SOLEN LUPPO CAKE BITE SADE 12sp 184g(CS)
    (
        rf"(\d+)\s*(?:штук|шт|pcs|adet|adt|ad|sp|pkt|pk)\s*(?:\*|×|х|Х|x|X])?\s*(\d+(?:[.,]\d+)?)\s*(?:грамм|грам|гр|г|gram|grm|gr|g|ml)(?:\s+|$)",
        lambda m: process_match(
            extract_float(m.group(2)), 1, int(m.group(1))
        ),
    ),
    #
    (
        rf"(\d+)(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kt|pkt|pk)\s*(?:\*|×|х|Х|x|X])?(\d+[.,]?\d*)\.?\s*(?:грамм|грам|гр|г|gram|grm|gr|g|ml)(?:.*)?(?:\s+|$)",
        lambda m: process_match(extract_float(extract_float(m.group(2))), 1, int(m.group(1))),
    ),
    # # Шоколадні цукерки BONART CHOCO COINS (монети)в пластиковій банці 100шт 500гр Х12
    # (
    #     rf".*?(\d+)\s*(?:шт|штук|pcs|ad|adt|adet)\s*(?:\*|x|X|х|Х])?\s*(\d+(?:[.,]\d+)?)\s*(?:грамм|грам|гр|г|gram|grm|gr|g|ml)\s*(?:\*|×|х|Х|x|X])?\s*(\d+)(?:\s+|$)",
    #     lambda m: process_match(
    #         extract_float(m.group(2)), int(m.group(1)), int(m.group(3))
    #     ),
    # ),
    # # Шоколадні цукерки (монетки) USD Chocolate Coin 2,5 г 200 шт Х 12 **********
    # (
    #     rf".*?(\d+(?:[.,]\d+)?)\s*(?:грамм|грам|гр|г|gram|grm|gr|g|ml)\s*(?:\*|×|х|Х|x|X])?(\d+)\s*(?:\*|×|х|Х|x|X])?\s*(?:штук|шт|pcs|adet|adt|ad|sp|pkt|pk)(?:\*|×|х|Х|x|X])?\s*(\d+)\s*(?:бл|блок|блоков|jar|jars|банка|банки|банці|kavanoz|tray|trays|лоток|лотки|tepsi|vase|vases|ваза|вазы|vazo|bag|bags|box|boxes|kutu|kt)",
    #     lambda m: process_match(
    #         extract_float(m.group(1)), int(m.group(2)), int(m.group(3))
    #     ),
    # ),

]