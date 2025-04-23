import ollama
import json

def process_sku(sku_text):
    """Обрабатывает одну строку SKU с помощью модели Ollama"""
    model_name = "gemma3:latest"  # используем доступную модель
    
    try:
        # Формируем запрос для модели
        prompt = f'''sku:{sku_text}.
              Извлеки в формате json.
                {{
                    "sku": str,  # Bubble Bubble Water(Fruits) 55mlx24pcsx12boxes
                    "grm": float,  # 55
                    "pcs_in_block": float,  # 24
                    "box_in_cartoon": int,  # 12
                    "pcs_type": str,  # ml
                    "box_type": str  # box
                }}
            '''
        
        # Используем функцию generate
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            stream=False
        )
        
        # Возвращаем ответ
        return response.response
    
    except Exception as e:
        return f"Ошибка при обработке '{sku_text}': {e}"

def main():
    # Список SKU для обработки
    sku_list = [
        "Mini Pudding(Angle Jar) 13gx100pcsx6jars",
        "Mini Pudding(Dragon Jar) 13gx100pcsx6jars",
        "Mini Pudding(KT Cat Jar) 13gx100pcsx6jars",
        "Mini Pudding(MK Mouse Jar) 13gx100pcsx6jars",
        "Sea horce jelly 35gx48pcsx6jars",
        "Small Pop 40gx12pcsx4trays",
        "Snake jelly 35gx48pcsx6jars",
        "Super Gun Spray Candy 30mlx20pcsx12boxes",
        "Twins eyeball Gummy 4g*100pcs*12jars",
        "Umbrella Bubble Water 55mlx24pcsx12boxes",
        "Windmill Bubble Water 55mlx24pcsx12boxes",
    ]
    
    # Обработка каждого SKU
    results = {}
    for sku in sku_list:
        print(f"Обработка: {sku}")
        result = process_sku(sku)
        results[sku] = result
        print(f"Результат: {result}")
        print("-" * 50)
    
    # Сохраняем все результаты в файл
    with open("sku_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"Все результаты сохранены в файл 'sku_results.json'")

if __name__ == "__main__":
    main()
