#!/usr/bin/env python3
"""
Утилита для извлечения и обработки блоков кода из текстовых файлов.

Использование:
    python code_block_extractor.py файл.md --format json --output extracted.json
    python code_block_extractor.py файл.md --analyze
    python code_block_extractor.py файл.md --convert yaml json --output converted.json
"""

import argparse
import sys
import os
import json
import yaml
import re
from collections import defaultdict


def extract_code_blocks(text):
    """Извлекает блоки кода из текста"""
    pattern = r'```(\w*)\s*(.*?)\s*```'
    return re.findall(pattern, text, re.DOTALL)


def parse_block(language, content):
    """Парсит блок кода в зависимости от языка"""
    language = language.lower()

    try:
        if language in ['json', '']:
            return json.loads(content)
        elif language in ['yaml', 'yml']:
            return yaml.safe_load(content)
        else:
            return content
    except Exception as e:
        print(f"Ошибка парсинга блока {language}: {e}")
        return content


def main(content: str = None):
    parser = argparse.ArgumentParser(description='Утилита для работы с блоками кода')
    parser.add_argument('file', help='Файл для обработки')
    parser.add_argument('--format', help='Только блоки указанного формата')
    parser.add_argument('--output', help='Файл для сохранения результатов')
    parser.add_argument('--analyze', action='store_true', help='Анализировать структуру данных')
    parser.add_argument('--convert', nargs=2, metavar=('FROM', 'TO'),
                        help='Конвертировать из одного формата в другой')

    # args = parser.parse_args()
    #
    # # Проверяем существование файла
    # if not os.path.exists(args.file):
    #     print(f"Файл не найден: {args.file}")
    #     return 1
    #
    # # Читаем файл
    # with open(args.file, 'r', encoding='utf-8') as f:
    #     content = f.read()

    # Извлекаем блоки кода
    blocks = extract_code_blocks(content)

    if not blocks:
        print("Блоки кода не найдены")
        return 0

    # # Фильтруем по формату, если указан
    # if args.format:
    #     blocks = [(lang, code) for lang, code in blocks if lang.lower() == args.format.lower()]

    # Парсим блоки
    parsed_blocks = []
    for lang, code in blocks:
        parsed = parse_block(lang, code)
        parsed_blocks.append({
            'language': lang if lang else 'not specified',
            'content': parsed,
            'raw': code
        })

    # Выполняем запрошенное действие
    if args.convert:
        from_format, to_format = args.convert
        converted = []

        for block in parsed_blocks:
            if block['language'].lower() == from_format.lower():
                try:
                    result = None
                    if to_format.lower() == 'json':
                        result = json.dumps(block['content'], indent=2, ensure_ascii=False)
                    elif to_format.lower() in ['yaml', 'yml']:
                        result = yaml.dump(block['content'], default_flow_style=False, allow_unicode=True)

                    if result:
                        converted.append(result)
                except Exception as e:
                    print(f"Ошибка конвертации: {e}")

        # Выводим или сохраняем результат
        output = "\n\n".join(converted)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Конвертированные данные сохранены в {args.output}")
        else:
            print(output)

    elif args.analyze:
        for i, block in enumerate(parsed_blocks, 1):
            print(f"\nБлок {i} ({block['language']}):")

            if isinstance(block['content'], (dict, list)):
                # Анализируем структуру
                if isinstance(block['content'], dict):
                    print(f"Словарь с {len(block['content'])} ключами:")
                    for key in list(block['content'].keys())[:10]:
                        value = block['content'][key]
                        print(f"  - {key}: {type(value).__name__}")

                elif isinstance(block['content'], list):
                    print(f"Список из {len(block['content'])} элементов:")
                    if block['content']:
                        types = defaultdict(int)
                        for item in block['content']:
                            types[type(item).__name__] += 1

                        print("  Типы данных в списке:")
                        for type_name, count in types.items():
                            print(f"    - {type_name}: {count} элементов")
            else:
                print(f"Текст ({len(block['raw'])} символов)")

    else:
        # По умолчанию просто выводим найденные блоки
        output = json.dumps(parsed_blocks, indent=2, ensure_ascii=False, default=str)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Результаты сохранены в {args.output}")
        else:
            print(output)

    return 0


if __name__ == '__main__':
    sys.exit(main())
