# Скачать и установить Ollama с официального сайта: https://ollama.com/download
# После установки запустить Ollama
# Убедиться, что модель "gemma3:latest" загружена (или изменить код, чтобы использовать другую доступную модель)

from datetime import datetime

import ollama
import re
import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
import os

async def async_ollama_generate(model: str, prompt: str) -> str:
    """
    Асинхронный запрос к Ollama API

    Args:
        model (str): Название модели
        prompt (str): Запрос к модели

    Returns:
        str: Ответ от модели
    """
    # Используем официальный Python-клиент Ollama
    # Запускаем синхронный код в асинхронном контексте
    loop = asyncio.get_event_loop()
    try:
        # Запускаем синхронный код в отдельном потоке
        response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
            # lambda: ollama.generate(model="model_name", prompt="Ваш запрос")
        )
        return response['message']['content']
    except Exception as e:
        print(f"Ошибка при запросе к Ollama API (chat): {e}")
        try:
            # Пробуем альтернативный метод
            response = await loop.run_in_executor(
                None,
                lambda: ollama.generate(model=model, prompt=prompt)
            )
            return response['response']
        except Exception as e2:
            print(f"Ошибка при запросе к Ollama API (generate): {e2}")
            raise Exception(f"Не удалось получить ответ от Ollama API: {e}, {e2}")


def clean_llm_json_response(response_text: str) -> Any:
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


async def process_single_sku(model_name: str, item: str) -> Dict[str, Any]:
    """
    Обрабатывает один SKU асинхронно

    Args:
        model_name (str): Название модели Ollama
        item (str): SKU для обработки

    Returns:
        Dict[str, Any]: Результат обработки
    """
    print(f"\nОбработка SKU: {item}")

    prompt = (f'''sku:{item}.'''
              '''Извлеки в формате json.
                {
                    "sku": str,  # оригинальный SKU
                    "grams_in_pcs": float,  # 55
                    "pcs_in_block": float,  # 24
                    "box_in_cartoon": int,  # 12
                    "weight_unit": float,  # g,ml,kg,гр,грм,кг,мл
                    "pcs_type": str,  # pcs,шт
                    "box_type": str  # jar,box,банка,блок
                }
            ''')

    # Асинхронный запрос к API
    response_text = await async_ollama_generate(model_name, prompt)

    # Очищаем и парсим ответ
    clean_json = clean_llm_json_response(response_text)

    # Выводим чистый JSON
    print("Очищенный JSON:")
    print(json.dumps(clean_json, ensure_ascii=False, indent=2))
    print("-" * 50)

    return {
        "original_sku": item,
        "parsed_data": clean_json
    }


async def main_async(text: List[str], save_to_file: bool = False) -> Optional[List[Dict[str, Any]]]:
    """
    Асинхронная основная функция для обработки списка SKU

    Args:
        text (List[str]): Список SKU для обработки
        save_to_file (bool): Сохранять результаты в файл

    Returns:
        Optional[List[Dict[str, Any]]]: Список результатов обработки или None в случае ошибки
    """
    model_name = "gemma3:latest"  # используем доступную модель

    try:
        # Создаем задачи для асинхронного выполнения
        tasks = [process_single_sku(model_name, item) for item in text]

        # Выполняем все задачи параллельно
        results = await asyncio.gather(*tasks)

        if save_to_file:
            # Сохраняем все результаты в файл
            with open("sku_results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print(f"\nВсе результаты сохранены в файл 'sku_results.json'")

        return results

    except Exception as e:
        import traceback
        print(f"Произошла ошибка: {e}")
        traceback.print_exc()
        return None


def main(text: List[str], save_to_file: bool = False) -> Optional[List[Dict[str, Any]]]:
    """
    Обертка для запуска асинхронной функции

    Args:
        text (List[str]): Список SKU для обработки
        save_to_file (bool): Сохранять результаты в файл

    Returns:
        Optional[List[Dict[str, Any]]]: Список результатов обработки или None в случае ошибки
    """
    return asyncio.run(main_async(text, save_to_file))


if __name__ == "__main__":
    from products_source import test_products
    print(f"Начало обработки... {datetime.now()}")
    main(test_products[:3], save_to_file=True)
    print(f"Конец обработки... {datetime.now()}")