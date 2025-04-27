import re
import json
import asyncio
from typing import Any

# Переносим основную синхронную логику в отдельную функцию
def _clean_llm_json_response_sync(response_text: str) -> Any:
    """
    Синхронная функция для извлечения JSON из ответа LLM.
    Используется для выполнения в отдельном потоке.
    """
    # Ищем содержимое между ```json ... ``` или ``` ... ```
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text, re.S)

    if json_match:
        json_str = json_match.group(1)
        # print("JSON found within ``` fences (sync part).") # Для отладки
    else:
        json_str = response_text
        # print("No ``` fences found, assuming entire response is JSON (sync part).") # Для отладки

    json_str = json_str.strip()

    if not json_str:
         # В синхронной части выбрасываем синхронное исключение
         raise ValueError("Извлеченная или входная строка JSON пуста.")

    try:
        json_obj = json.loads(json_str)
        return json_obj
    except json.JSONDecodeError as e:
        # Улучшенное сообщение об ошибке
        preview_len = 200
        json_str_preview = json_str[:preview_len] + ('...' if len(json_str) > preview_len else '')
        # В синхронной части выбрасываем синхронное исключение
        raise ValueError(f"Не удалось распарсить JSON. Ошибка: {e}. "
                         f"Попытка парсинга строки (начало): '{json_str_preview}'") from e

async def clean_llm_json_response(response_text: str) -> Any:
    """
    Асинхронно извлекает JSON из ответа LLM, убирая Markdown-разметку ```json или ```.

    Выполняет CPU-связанную логику в отдельном потоке, чтобы не блокировать
    основной цикл событий asyncio.

    Если разметка не найдена, функция предполагает, что весь входной текст
    является JSON-строкой.

    Args:
        response_text (str): Исходный ответ от LLM, возможно содержащий Markdown-разметку.

    Returns:
        dict/list: Распарсенный JSON объект.

    Raises:
        ValueError: Если не удалось найти или распарсить JSON в отдельном потоке.
    """
    # Запускаем синхронную логику в отдельном потоке и ожидаем ее завершения
    # Это позволяет event loop'у выполнять другие задачи, пока парсинг происходит.
    try:
        json_obj = await asyncio.to_thread(_clean_llm_json_response_sync, response_text)
        return json_obj
    except ValueError as e:
        # Перехватываем исключение, выброшенное в другом потоке, и выбрасываем его дальше
        print(f"Ошибка при выполнении парсинга в отдельном потоке: {e}") # Для отладки
        raise e # Перевыбрасываем исключение

# Пример использования (в асинхронном контексте)
async def main():
    response_with_markdown = """
    ```json
    {
      "name": "test",
      "value": 123,
      "is_valid": true
    }
    ```
    """

    response_without_markdown = """
    {
      "list_data": [1, 2, 3]
    }
    """

    invalid_response = """
    ```json
    {
      "incomplete_json":
    }
    ```
    """

    text_without_json = "This is just plain text."

    try:
        json_data1 = await clean_llm_json_response(response_with_markdown)
        print("Parsed JSON 1:", json_data1)

        json_data2 = await clean_llm_json_response(response_without_markdown)
        print("Parsed JSON 2:", json_data2)

        # Следующий вызов выбросит исключение
        # json_data3 = await clean_llm_json_response(invalid_response)
        # print("Parsed JSON 3:", json_data3)

        # Следующий вызов выбросит исключение (если ожидается JSON, но его нет)
        # json_data4 = await clean_llm_json_response(text_without_json)
        # print("Parsed JSON 4:", json_data4)


    except ValueError as e:
        print(f"Error during parsing: {e}")

    # Пример, демонстрирующий, что цикл событий не блокируется (если бы парсинг был долгим)
    # while True:
    #     await asyncio.sleep(1)
    #     print("Main loop is running...")


if __name__ == "__main__":
    # Для запуска асинхронной функции верхнего уровня
    asyncio.run(main())