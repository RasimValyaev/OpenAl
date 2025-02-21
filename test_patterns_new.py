import re
from typing import List, Tuple, Optional
from nomenclature_patterns_my import nomenclature_pattern
import pandas as pd
from datetime import datetime
from products_source import test_products


def find_match(text: str, patterns: List[Tuple]) -> Optional[Tuple[str, int, int]]:
    """Try to match text against a list of patterns and return extracted values."""
    for pattern, handler in patterns:
        match = re.search(pattern, text.lower())  # Using search instead of match to find pattern anywhere in text
        if match:
            try:
                lst = list(handler(match))
                lst.append(pattern)
                return tuple(lst)
            except (ValueError, IndexError):
                continue
    return None


def format_result(sku:str, weight: str, pieces: int, boxes: int, pattern:str, parsed=False) -> dict:
    return {
        "sku": sku,
        "weight": weight,
        "pieces": pieces,
        "box": boxes,
        "pattern": pattern,
        "parsed": parsed,
    }


def extract_data_from_text(text:str)->dict:
    result = find_match(text, nomenclature_pattern)
    if result:
        weight, pieces, boxes, pattern = result
        formatted = format_result(text, weight, pieces, boxes, pattern, True)
    else:
        formatted = format_result(text, None, None, None, None, False)
    return formatted


if __name__ == "__main__":
    total = []
    df = pd.DataFrame()
    for text in test_products:
        result = extract_data_from_text(text)
        total.append(result)
        print("-" * 80)

    columns = list(total[0].keys())
    df = pd.DataFrame(total, columns=columns)
    df.sort_values("parsed",ascending=False,inplace=True)
    df.drop(columns="parsed", axis=1,inplace=True)
    print(df.to_string())
    filename = f"df_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(filename,index=False)
