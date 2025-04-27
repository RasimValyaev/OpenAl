import ollama
import re
import json


def clean_llm_json_response(response_text):
    """
    Извлекает JSON из ответа LLM, убирая Markdown-разметку.

    Args:
        response_text (str): Исходный ответ от LLM, возможно содержащий Markdown-разметку

    Returns:
        dict/list: Распарсенный JSON объект
    """
    # Ищем содержимое между ```json и ```
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)

    if json_match:
        # Если нашли разметку, извлекаем содержимое
        json_str = json_match.group(1)
    else:
        # Если разметки нет, предполагаем, что весь текст - это JSON
        json_str = response_text

    # Очищаем строку от возможных лишних пробелов и символов
    json_str = json_str.strip()

    # Преобразуем строку в JSON объект
    try:
        json_obj = json.loads(json_str)
        return json_obj
    except json.JSONDecodeError as e:
        raise ValueError(f"Не удалось распарсить JSON: {e}")


def main(text):
    # Укажите имя модели, с которой хотите взаимодействовать
    model_name = "gemma3:latest"  # используем доступную модель
    results = []

    try:
        # Подключение к Ollama API и генерация ответа
        for item in text:
            print(f"\nОбработка SKU: {item}")
            prompt = (f'''sku:{item}.'''
              '''Извлеки в формате json.
                {
                    "sku": str,  # Bubble Bubble Water(Fruits) 55mlx24pcsx12boxes
                    "grams_in_pcs": float,  # 55
                    "pcs_in_block": float,  # 24
                    "box_in_cartoon": int,  # 12
                    "pcs_type": str,  # ml
                    "box_type": str  # box
                }
            ''')

            # Используем функцию generate вместо make_request
            response = ollama.generate(
                model=model_name,
                prompt=prompt,
                stream=False  # False для получения ответа сразу
            )

            # Очищаем и парсим ответ
            clean_json = clean_llm_json_response(response.response)

            # Выводим чистый JSON
            print("Очищенный JSON:")
            print(json.dumps(clean_json, ensure_ascii=False, indent=2))

            # Добавляем результат в список
            results.append({
                "original_sku": item,
                "parsed_data": clean_json
            })

            print("-" * 50)
        #
        # # Сохраняем все результаты в файл
        # with open("sku_results.json", "w", encoding="utf-8") as f:
        #     json.dump(results, f, ensure_ascii=False, indent=4)
        #
        # print(f"\nВсе результаты сохранены в файл 'sku_results.json'")
        # return results

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None


if __name__ == "__main__":
    data = [
            "Mini Pudding(Angle Jar) 13gx100pcsx6jars",
            "Umbrella Bubble Water 55mlx24pcsx12boxes",
            "Windmill Bubble Water 55mlx24pcsx12boxes",
        ]
    main(data)