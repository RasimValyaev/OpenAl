import re
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from products import test_products
from nomenclature_extract_pattern import nomenclature_pattern
import os
import shutil


class ProductParser:
    def __init__(self):
        self.patterns = nomenclature_pattern

    def _detect_container_type_re(self, text: str) -> str:
        """Detect container type using regular expressions"""
        text_lower = text.lower()

        if any(x in text_lower for x in ["jar", "jars", "банка", "банки", "банці","kavanoz"]):
            return "jar"
        elif any(x in text_lower for x in ["tray", "trays", "лоток", "лотки", "tepsi"]):
            return "tray"
        elif any(x in text_lower for x in ["vase", "vases", "ваза", "вазы", "vazo"]):
            return "vase"
        elif any(x in text_lower for x in ["bag", "bags"]):
            return "bag"
        elif any(x in text_lower for x in ["бл", "блок", "box", "boxes", "кт"]):
            return "box"
        return "box"  # default

    def parse_product(self, text: str) -> Dict:        
        weight, pieces, containers = 0.0, 1, 1
        weight_unit = "ml" if "ml" in text.lower() else "g"
        parsed = False
        pattern = ""
        for pattern, extractor in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    weight, pieces, containers = extractor(match)
                    parsed = True
                    break
                except (ValueError, IndexError):
                    continue

        if parsed:
            return {
                "sku": text,
                "weight": weight,
                "weight_unit": weight_unit,
                "pieces": pieces,
                "containers": containers,
                "container_type": self._detect_container_type_re(text),
                "pattern": pattern,
                "parsed": True 
            }
            
        return {
            "sku": text,
            "weight": 0.0,
            "weight_unit": "",
            "pieces": 1,
            "containers": 1,
            "container_type": "",
            "pattern": "",
            "parsed": False
        }

    def parse_products(self, products: List[str]) -> pd.DataFrame:
        """Парсинг списка продуктов"""
        data = []
        success = 0
        failed = 0

        for text in products:
            result = self.parse_product(text)
            data.append(result)
            if result["parsed"]:
                success += 1
            else:
                print(f"Failed to parse: {text}")
                failed += 1

        # Create DataFrame
        df = pd.DataFrame(data)
        if data:
            # сортировка по убыванию. Вначеле успешно распарсенные
            df = df.sort_values("parsed", ascending=False)

            # Удаляем колонку parsed
            df = df.drop("parsed", axis=1)

            # Display results
            print("\nProducts table:")
            print(df.to_string(index=False))  # Выводим таблицу продуктов

            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            df.to_excel(f"parser_results_{timestamp}.xlsx", index=False)

        # Statistics
        total = success + failed
        print(f"\nStatistics:")
        print(f"Total products: {total}")
        print(f"Successfully parsed: {success} ({success/total*100:.1f}%)")
        if failed > 0:
            print(f"Failed to parse: {failed} ({failed/total*100:.1f}%)")

        # Container type statistics
        if success > 0:
            containers = df["container_type"].value_counts()
            print("\nContainer types used:")
            for container, count in containers.items():
                if container:  # Skip empty values
                    print(f"{container}: {count} ({count/success*100:.1f}%)")
        return df


def create_backup(model_path):
    """Создание резервной копии модели"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = model_path.split('.')[-2]
    backup_path = f"{model_name}_backup_{timestamp}.pkl"
    if os.path.exists(model_path):
        shutil.copy(model_path, backup_path)
        print(f"Резервная копия создана: {backup_path}")
    else:
        print("Файл модели не найден.")


def main_product_parser_re():

    # Создаем парсер и запускаем
    parser = ProductParser()
    return parser.parse_products(test_products)


if __name__ == "__main__":
    main_product_parser_re()
