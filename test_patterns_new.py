from os import name
import re
from typing import List, Tuple, Optional
from nomenclature_patterns_my import nomenclature_pattern
import pandas as pd 


def find_match(text: str, patterns: List[Tuple]) -> Optional[Tuple[float, int, int]]:
    """Try to match text against a list of patterns and return extracted values."""
    for pattern, handler in patterns:
        match = re.search(pattern, text)  # Using search instead of match to find pattern anywhere in text
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


# Test cases from real data
test_cases = [
    'Рулет "ALPELLA" молочный коктейль с абрикосом 290,25г*12шт №573',
    'Шок.кон."Карнавал" 330гр*6шт бол.сердце пл. фундук №837-3',
    'Рулет "Peki" с какао кремом 150г*15шт/Хамле №7105',
    'Шоколад "Мадлен" 430гр*14шт № 91005451',
    'Шок.кон."Розалина" 280гр*10шт молочный коколин № 8004',
    'Шоколадна фігурка "Ozmo Go" 30g з молочного, білого та чорного шоколаду 20шт Х 4бл',
    'Шок.кон."Карнавал" 330гр*8шт мал.овал пл. шоколад №836-13',
    'Шоколадні цукерки (монетки) USD Chocolate Coin 2,5 г 200 шт Х 12',
    'Шоколадні цукерки BONART CHOCO COINS (монети)в пластиковій банці 100шт 500гр Х12',
    'Печиво "GORONA MARIE" з апельсиновим смаком 120гр х24',
    'Печиво "GOCCIOLOTTI" пісочне зі шматочками шоколаду 350 г х 12 шт',
    'Печиво "CHOCO PAYE" з маршмеллоу покрите шоколадною глазур\'ю і кокосовою стружкою 216гр х12',
    'Печиво "BREAKFAST" цільнозернове зі злаками, яблуком та корицею 350 г х 10 шт',
    'Печиво "BISKREM" з шоколадом 205гр Х 12шт',
    'Печиво "BISKIATO" сендвіч з шоколадним кремом 160гр х24',
    'Печиво "HALLEY" 300 гр Х 12 шт',
    'Печиво «BISCOLATA STARZ» з молочним кремом в молочному шоколаді 82г Х24шт',
    'Печиво "ZUPPOLE" пісочне зі свіжим молоком і цукровою посипкою 350 г х 12 шт',
    'Печиво "Simley " сендвіч з маршмеллоу покрите глазур\'ю 19гр.Х 24 Х 6',
    'Печиво "SFOGLIATINE" листкове глазуроване з абрикосом 200 г х 15 шт',
    'Яйце шоколадне "ANIMAL WORLD " з іграшкою в середині 25 гр 24Х6бл',
    'Печ.сах. "Лора" с маршмаллоу со вкусом клубники глазированное 30г*60шт №302',
]


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
    for text in test_cases:
        result = extract_data_from_text(text)
        total.append(result)
        print("-" * 80)

    columns = list(total[0].keys())
    df = pd.DataFrame(total, columns=columns)
    df = df.sort_values("parsed",ascending=False)
    df.drop(columns="parsed", axis=1,inplace=True)
    print(df.to_string())
    df.to_excel("df.xlsx",index=False)
