import re
from typing import List, Tuple, Optional
from nomenclature_patterns_new import nomenclature_pattern, extract_float

def find_match(text: str, patterns: List[Tuple]) -> Optional[Tuple[float, int, int]]:
    """Try to match text against a list of patterns and return extracted values."""
    for pattern, handler in patterns:
        match = re.search(pattern, text)  # Using search instead of match to find pattern anywhere in text
        if match:
            try:
                return handler(match)
            except (ValueError, IndexError):
                continue
    return None

def format_result(weight: float, pieces: int, boxes: int) -> str:
    """Format the result string based on the number of parameters."""
    if boxes > 1 and pieces > 1:
        return f"{weight}г x {pieces}box x {boxes}"
    elif boxes > 1:
        return f"{weight}г x {pieces}шт x {boxes}"
    else:
        return f"{weight}г x {pieces}шт"

# Test cases from real data
test_cases = [
    'Рулет "ALPELLA" молочный коктейль с абрикосом 290г*12шт №573',
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